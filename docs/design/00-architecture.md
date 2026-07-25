# Go Jellyfin server: architecture

Status: design. This document decides. Where a real tradeoff exists it states the options, picks
one, and records why. A future session should be able to read this cold and start building.

Progress in this project is measured in **verification gates passed**, not time. The bottleneck is
verification throughput, not code volume. There are no hour/day/week estimates anywhere in this
document, by policy.

Companion analysis (read these first; every claim below cites into them or into the C# source):

- `docs/analysis/01-route-inventory.md` — all 419 routed operations, spec membership, plane
- `docs/analysis/02-plane-assignment.md` — control / transcode / out-of-scope split
- `docs/analysis/03-streambuilder-decision-tree.md` — direct play vs stream vs transcode
- `docs/analysis/04-encodinghelper-shape.md` — ffmpeg argv dimensionality
- `docs/analysis/05-scheduled-tasks.md` — CronJob candidates
- `docs/analysis/06-manager-coupling.md` — in-process state to relocate

## 0. The premise, restated as an invariant

The C# source in this repo is the **specification and the oracle**. It is not code we refactor. It
can be built and run to emit golden fixtures. Every behaviour of the Go server is correct if and
only if it matches what this C# server does on the wire, for the requests real clients send.

Two design rules follow and are non-negotiable:

1. **The contract is the wire, not the OpenAPI spec.** 52 of the 279 in-scope operations are
   invisible in the published spec (`docs/analysis/02-plane-assignment.md`), including every HLS
   segment endpoint clients actually stream from. Building to the spec builds the wrong server.
2. **Transliterate, do not redesign** `EncodingHelper`, `StreamBuilder`, and `Emby.Naming`. Those
   lines encode empirical knowledge about driver quirks and release-naming conventions that cannot
   be re-derived. Redesigning them is the single most likely way this project fails.

---

## 1. Repo strategy

### Decision: sibling repository, C# fork pinned read-only as a git submodule at a tagged commit.

The Go server lives in a new repository, `jellyfin-go` (name TBD). This C# fork is vendored into it
as a git submodule under `oracle/`, pinned to a specific tag, never tracked to a moving branch.

### Options considered

| Option | Verdict |
|:--|:--|
| **A. In-tree subdirectory** — Go code in `/server-go` inside this fork | Rejected. Inherits the fork's rebase pain: every upstream sync churns the tree the Go build sits in. Couples Go CI to a 296k-line C# solution's build graph. Blurs the oracle/implementation line the whole project depends on. |
| **B. Sibling repo, fork vendored as submodule at a tag** | **Chosen.** |
| **C. Sibling repo, fork referenced only by documentation** | Rejected. We *must* be able to build and run the oracle deterministically to emit fixtures. A prose reference cannot be checked out at a known-good commit in CI. |

### Why B

- **The oracle must be buildable and reproducible.** Fixture generation (§3) and the differential
  harness (§4) both compile and run the C# server. A submodule pinned to a tag gives CI a
  byte-identical oracle on every run. Upstream moves are opt-in: bump the submodule pointer
  deliberately, regenerate fixtures, observe the diff. The oracle version is a reviewable line in a
  commit, not an ambient fact.
- **No inherited rebase pain.** We never rebase the fork. It is read-only at a tag. If we later want
  a newer Jellyfin, we move the tag and re-run the conformance suite — the suite tells us exactly
  what wire behaviour changed. That is a feature: version bumps become measured events.
- **Clean separation of concerns.** The Go repo owns Go build, Go CI, Kubernetes manifests. The
  submodule owns the spec. A reader is never confused about which tree is authoritative.

### Concrete layout

```
jellyfin-go/
  oracle/                     # git submodule -> this fork, pinned at tag oracle-v12.0.0
  cmd/
    controlplane/
    transcodeplane/
  internal/
    streambuilder/            # transliteration of MediaBrowser.Model/Dlna/StreamBuilder.cs
    encodinghelper/           # transliteration of MediaBrowser.Controller/MediaEncoding/EncodingHelper.cs
    naming/                   # transliteration of Emby.Naming
    ...
  conformance/                # capture harness + replay runner (§3)
  differential/               # ffmpeg-argv diff harness (§4)
  fixtures/                   # golden captures, checked in, generated from oracle/
  deploy/                     # K8s manifests, CRD definitions + reconciler (§6)
  docs/
```

The pinned tag for the first cycle is the current tip of this fork, `AssemblyVersion 12.0.0`
(`SharedVersion.cs:3`), commit `71ab342`.

### Flagged

The oracle build requires the .NET SDK, which is **not present in this session's environment**
(`which dotnet` → not found). Fixture generation and the differential harness therefore cannot run
here; they run in the Go repo's CI where the SDK is installed. Every gate in §7 that depends on the
oracle is explicit about needing that toolchain.

---

## 2. Plane boundary

### The split

From `docs/analysis/02-plane-assignment.md`: 279 in-scope operations.

| Plane | Ops | What it owns |
|:--|--:|:--|
| **Control** | 251 | DB reads/writes returning JSON, plus static-file reads (images, trickplay tiles). No long-lived per-request resource. Stateless. Scales 0→N. Hibernates. |
| **Transcode — pinned** | 24 | Owns an ffmpeg process + segment scratch dir for a session's lifetime. Lives on GPU nodes. Scales on active encode count. Pods individually disposable. |
| **Transcode — cacheable** | 4 | Subtitle/attachment extraction. Spawns ffmpeg but output is short and content-addressed. No affinity. Scales independently. |

The two-way split of the transcode plane is a real decision, not cosmetics: pinned and cacheable
have different scaling laws and different affinity needs. The pinned plane's *substrate* — GPU node
pool, hardware-acceleration type, per-session scratch template, and warm-capacity envelope — is
admin desired-state, declared by a `TranscodePool` CRD (§6); each individual session runs in its own
pod scheduled onto that pool (`TranscodeSession`, §5).

### Ingress routing: path-prefix on a single hostname

**Decision: route by URL path prefix on one hostname. Do not rewrite `TranscodingUrl` hosts.**

Justification is empirical. The C# server emits **relative** segment URIs. `DynamicHlsController.cs:1420`
passes the literal string `"hls1/main/"` as the segment prefix, and `DynamicHlsPlaylistGenerator.cs:91-97`
appends the original query string to each relative URI. There is no host in the playlist. A client
resolves segments against the same origin it fetched the playlist from. Therefore a single hostname
with path-based routing at the ingress is sufficient and is what clients already expect. Host
rewriting would be a gratuitous new behaviour we would have to prove safe across five client
families; relative URIs make it unnecessary.

The path split is not a clean two-prefix rule. `/Audio/*` is entirely transcode plane. `/Videos/*`
straddles: `/Videos/{id}/stream` and `/Videos/{id}/hls1/...` are transcode, while
`/Videos/{id}/Trickplay/...`, `/Videos/{id}/AdditionalParts`, and `/Videos/{id}/Subtitles` (upload)
are control (`docs/analysis/02-plane-assignment.md`). The ingress needs ordered, depth-aware rules.
Sketch (Envoy/nginx-expressible):

```
# transcode plane (pinned)
  prefix  /Audio/                              -> transcode        # entire /Audio subtree
  regex   ^/Videos/[^/]+/(stream|master\.m3u8|main\.m3u8|live\.m3u8|hls/|hls1/)  -> transcode
  exact   /Videos/ActiveEncodings              -> transcode
# transcode plane (cacheable)
  regex   ^/Videos/[^/]+/[^/]+/Subtitles/.*/Stream\.  -> transcode-cacheable
  regex   ^/Videos/[^/]+/[^/]+/Subtitles/[^/]+/subtitles\.m3u8 -> transcode-cacheable
  regex   ^/Videos/[^/]+/[^/]+/Attachments/    -> transcode-cacheable
# everything else
  prefix  /                                    -> control
```

The transcode rules are listed first and are specific; the control plane is the default. This is
maintainable because the transcode surface is only 28 operations across a handful of path shapes,
and it is fully enumerated in the analysis.

### Session affinity for segment requests

**Decision: one pod per transcode session (§5's `TranscodeSession` model). The ingress routes on the
`playSessionId` query parameter to that session's dedicated pod via an operator-maintained endpoint;
there is no consistent hashing and no per-request claim-table lookup.**

The routing *key* is forced by the source. The in-process job registry (`TranscodeManager.cs:48`,
`List<TranscodingJob>`) is keyed by `playlistPath` =
`MD5(mediaPath + "-" + UserAgent + "-" + deviceId + "-" + playSessionId)`
(`StreamingHelpers.cs:384`). The `playlistId` path segment is **not** the key — it is the constant
string `main` (`DynamicHlsController.cs:1420`, parameter annotated `CA1801:ReviewUnusedParameters`
at `:1090`). So affinity cannot key on the path segment; it must key on the query. Because
`DynamicHlsPlaylistGenerator.cs:91-97` appends the whole original query string to every segment URI,
`playSessionId` rides along on every segment request, and it is the coarsest key that keeps one
session on one pod.

The *mechanism* is where the pod-per-session model (§5) simplifies things. When playback negotiation
starts a transcode, the control plane mints a `TranscodeSession` CR; the operator reconciles it into
one dedicated pod and publishes that pod as a stable per-session endpoint — the CNPG pattern, where
the operator keeps a Service pointing at the cluster's current primary as pods move. The transcode
ingress routes `playSessionId → that endpoint`. No hashing (the pod *is* the session, so there are no
slots to rebalance) and no claim-table read per segment (the endpoint is the mapping, updated by the
operator only when the pod is created or recreated, not per request). One session split across pods —
the failure the old hashing-plus-claim design worked to prevent — is now structurally impossible: a
session is a pod.

This supersedes an earlier draft that hashed `playSessionId` to a shared transcode fleet and used a
Postgres claim table as the tiebreak authority. That worked, but it existed only because a
multi-tenant pod is not per-session addressable; making the pod the session removes the need for both
the hash and the table (§5).

### Flagged for runtime experiment

`User-Agent` is part of the MD5 job key. A client that varies its UA within a session forks a second
ffmpeg job in the C# server. Our affinity keys on `playSessionId`, which would keep both jobs on one
pod — behaviourally fine, but it means our job-dedup key must still include UA to match the oracle's
job *count* and its `ActiveEncodings` bookkeeping. Confirm whether any real client varies UA
mid-session before finalizing the job-identity key on the transcode plane.

---

## 3. Conformance strategy: capture and replay

This infrastructure is built **before** the code it verifies. It is the reason the whole project is
tractable.

### Capture harness

A recording proxy sits between real clients and a real (C#) Jellyfin server. For every exchange it
logs: full request (method, path, all query params, headers, body), full response (status, headers,
body), the wall-clock time, and a **client tag** derived from `User-Agent` + `X-Emby-Authorization`
device fields so exchanges can be grouped per client family (Swiftfin, findroid, Streamyfin, Android
TV, Kodi).

Deployment: the proxy is a thin Go reverse proxy with a `record` mode. It is pointed at a Jellyfin
instance loaded with a fixed, synthetic media library (see below). Real client apps are driven
through representative flows — login, browse, resume, play (direct play, direct stream, transcode),
seek, subtitle toggle, mark-watched. Captures are written as newline-delimited JSON, one file per
client family, checked into `fixtures/capture/`.

The captured Jellyfin responses **are the golden fixtures.** There is no hand-authored expected
output. The oracle produces truth; we record it.

### Replay runner

The replay runner reads captured request/response pairs, replays each request against the Go server,
and diffs the Go response against the captured Jellyfin response. A diff is a gate failure.

Replay is **stateful and ordered per session**: a resume request depends on a prior progress report.
The runner replays a client's exchanges in capture order against a Go server seeded with the same
synthetic library and user set, so that IDs and state line up.

### Normalization rules

Responses are not byte-identical across runs; some fields are legitimately non-deterministic. The
differ normalizes before comparing. These rules are themselves part of the contract and are
version-controlled.

| Field class | Rule |
|:--|:--|
| **Item IDs** (`Guid`) | Deterministic in the synthetic library — seeded from item path, so Go and oracle produce identical GUIDs. Not normalized; a mismatch is a real bug. |
| **Auth tokens / `AccessToken`** | Replaced with a placeholder `<token>` on both sides before diff. Tokens are random by construction. |
| **`ServerId`, session IDs, `PlaySessionId`** | Normalized to stable placeholders by first-seen order within a capture. Structural identity preserved (same placeholder ⇒ same value), value ignored. |
| **Timestamps** (`DateCreated`, `PremiereDate`, etc.) | ISO-8601 fields normalized to a canonical form; wall-clock "now"-derived fields (`DateLastActivity`) replaced with placeholder. |
| **Tick values** (`RunTimeTicks`, `*PositionTicks`) | **Not normalized.** These are content-derived and must match exactly. A tick mismatch is a real bug — this is where subtle transcode/seek errors surface. |
| **Field ordering in JSON objects** | Normalized (deep sort by key) before diff. JSON object order is not part of the contract. |
| **Array ordering** | **Not normalized.** `/Items` result order is a contract (sort options). A reordering is a real bug. |
| **`TranscodingUrl` and segment URIs** | Query-param order within the URL normalized; the param *set and values* compared exactly. |
| **Casing of property names** | The API serves both camelCase and PascalCase (`BaseJellyfinApiController` `[Produces]` includes both media types). The differ compares within the casing the request's `Accept` header selected. |

### Gate

Conformance passes for a client family when every captured exchange for that family replays with a
zero normalized diff. Per-family, so partial progress is measurable (Swiftfin green while Kodi is
still red).

---

## 4. Differential harness for the transcode port

Separate from conformance because it does not need a running server, media files, or a GPU — and
therefore **runs in CI on every commit**.

### Mechanism

`EncodingHelper` and `StreamBuilder` are pure functions of their inputs. The harness feeds an
**identical `DeviceProfile` + `MediaSourceInfo` + `EncodingOptions`** into both implementations and
diffs the output:

- For `StreamBuilder`: the resulting `StreamInfo` (PlayMethod, SubProtocol, container, codec lists,
  subtitle method, `TranscodeReasons` bitfield). Zero-diff required.
- For `EncodingHelper`: the resulting **ffmpeg argv** — the full command line, tokenized, compared
  element by element. Zero-diff required.

### How both sides run without media or a GPU

The C# side is invoked as a thin test harness linked against the oracle submodule, exposing
`EncodingHelper.GetVideoArguments` / `StreamBuilder.BuildVideoItem` over a JSON stdin/stdout
protocol. No ffmpeg is executed — we capture the **argv it would run**, not its output. No media
file is opened — `MediaSourceInfo` is a plain data object describing streams; it is constructed
synthetically.

The **critical enabler** (from `docs/analysis/04-encodinghelper-shape.md`): the driver-probe results
that gate argv construction (`IMediaEncoder.IsVaapiDeviceInteliHD`, ffmpeg version, etc.) are
**injected as a fixed synthetic capability set**, not probed from the host. Both implementations
receive the same synthetic `IMediaEncoder` facts. This makes the diff a pure function of the inputs
and independent of the CI runner's hardware — which is mandatory, because otherwise results depend on
whatever GPU the runner has.

### Corpus

The corpus is a matrix of `(DeviceProfile, MediaSourceInfo, injected-capabilities)` triples chosen to
exercise the reachable combinations of the 10 argv-producing pipelines × tonemap × deinterlace ×
subtitle-burn-in × driver-quirk flags. The corpus is grown by **capturing real `PlaybackInfo`
negotiations** from §3 (the `DeviceProfile`s five real client families actually send) crossed with
the synthetic library's `MediaSourceInfo`s and a curated set of injected capability profiles (Intel
iHD, Intel i965, AMD VAAPI, NVIDIA, Apple VT, RKMPP, software).

### Gate

Every corpus triple produces identical tokenized argv (EncodingHelper) and identical `StreamInfo`
(StreamBuilder) across both implementations. Runs in CI, no media, no GPU. This is the primary
regression guard for the highest-risk code.

---

## 5. Data model

Postgres. No SQLite-shaped assumptions. The C# server's `IJellyfinDatabaseProvider` /
`FastConcurrentLru` / EF patterns are relocated, not mirrored.

### BaseItemDto: stored vs computed

`BaseItemDto` has 155 properties (`MediaBrowser.Model/Dto/BaseItemDto.cs`). They are not 155 columns.
They decompose three ways:

| Class | Examples | Storage |
|:--|:--|:--|
| **Intrinsic stored** | `Id`, `Name`, `Path`, `Container`, `RunTimeTicks`, `ParentId`, `Type`, `PremiereDate`, provider IDs | Columns on `item`. |
| **Structured child data** | `MediaStreams`, `MediaSources`, `Chapters`, `People`, `Genres`, `Studios`, image tags | Separate tables (`media_stream`, `media_source`, `item_person`, …) joined on `item_id`. |
| **Per-user computed** | `UserData` (played, playback position, favorite, rating), `PlayedPercentage` | `user_item_data` table keyed `(user_id, item_id)`; merged into the DTO at serialization. |
| **Purely computed** | `ChildCount`, `RecursiveItemCount`, `CanDelete`, `CanDownload`, image blur-hashes when derivable | Not stored. Computed per request from other tables / policy. |

The DTO is **assembled at the edge**, not stored. This mirrors the C# `DtoService`, which projects a
`BaseItem` + `UserItemData` + policy into a `BaseItemDto`. We store the normalized item graph and
project on read. `docs/analysis/06-manager-coupling.md` confirms `UserManager` is already fully
DB-backed (no in-process state), so the user/policy side ports cleanly.

The `app_user` row has **two owners**, split along the same spec/status seam the CRDs use (§6). Its
identity and policy columns (`username`, `enabled`, admin flag, `policy`) are **reconciler-owned**,
projected from the `User` CR; the row's runtime companion `user_item_data` is **API-owned**, written
by playstate calls at streaming frequency. The API serves the identity/policy columns read-only.
This is why users are a CRD *and* Postgres rows at once, not one or the other — see §6.

Core tables (illustrative, not exhaustive):

```
item(id uuid pk, type text, name text, parent_id uuid, path text, container text,
     runtime_ticks bigint, premiere_date timestamptz, production_year int,
     date_created timestamptz, sort_name text, ... , provider_ids jsonb)
media_source(id uuid pk, item_id uuid fk, protocol text, path text, container text,
             bitrate bigint, run_time_ticks bigint, ...)
media_stream(media_source_id uuid fk, index int, type text, codec text, profile text,
             level text, channels int, sample_rate int, bit_depth int, is_default bool,
             is_forced bool, language text, ... , primary key (media_source_id, index))
item_person(item_id uuid fk, person_id uuid fk, role text, type text, sort_order int)
user_item_data(user_id uuid, item_id uuid, played bool, play_count int,
               playback_position_ticks bigint, is_favorite bool, rating double precision,
               last_played_date timestamptz, primary key (user_id, item_id))
app_user(id uuid pk, username text unique, enabled bool, ... policy jsonb)  -- identity/policy reconciled from User CR (§6)
device(id text pk, user_id uuid, app_name text, app_version text, last_activity timestamptz)
device_capabilities(device_id text pk, capabilities jsonb)   -- see below
```

`GET /Items`'s 88 query parameters (`ItemsController.cs:173`) become a query builder over `item` +
joins. The parameter set is large but mechanical; it is a filter/sort/paginate surface, and each
parameter maps to a WHERE/ORDER clause. The `InternalItemsQuery` in the C# source is the
specification for how each parameter composes.

### Where session state lives

From `docs/analysis/06-manager-coupling.md`:

| State | C# home | New home |
|:--|:--|:--|
| Active sessions | `SessionManager._activeConnections` (`:64`) | `session` table (Postgres). Key reproduces `appName + deviceId` concatenation (`:478`) **exactly**, separatorless collisions included. |
| Device capabilities | `DeviceManager._capabilitiesMap` (`:33`) — **in-memory only, not persisted** | `device_capabilities` table. This is authoritative state, not a cache: a client posts caps once, then streams; a different pod must find them. |
| Live-stream handles | `MediaSourceManager._openStreams` (`:61`) | `live_stream` row keyed `liveStreamId`; the handle itself is pod-local on the transcode plane. |
| Refresh progress | `ProviderManager._activeRefreshes` (`:65`) | `refresh_progress` row, or dropped with live progress reporting. |
| WebSocket fan-out | in-process event handlers | Redis pub/sub or Postgres `LISTEN/NOTIFY`. Sessions on any pod receive `Playing`/`Playstate`/`GeneralCommand` messages. |
| Item cache | `LibraryManager._cache` LRU (`:89`) | Dropped initially. Per-pod caches widen the stale-read window; add a shared cache only when a measurement demands it. |

### Where transcode session state lives

This is the crux of the whole architecture — the in-process job list is the single fact that makes
Jellyfin unscalable (§0). To relocate it correctly we have to understand what `TranscodeManager`
actually does, mechanism by mechanism, and then decide a home for each.

The model is the **CloudNativePG shape**. A `TranscodeSession` custom resource is the durable
*shape* of one session; an operator reconciles it into **one dedicated pod** that holds every live
mechanism. Just as a CNPG `Cluster` CR declares a database and is *not* rewritten when a row is
inserted, the `TranscodeSession` CR declares a transcode and is *not* rewritten when a segment is
produced or a keepalive ping arrives — all of that lives in the pod. The rule: **shape and lifecycle
go in the CR (≈ two writes: create, delete); every high-frequency mechanism stays in the pod;
nothing per-segment or per-ping ever touches etcd.** This supersedes an earlier draft that kept
identity and keepalive in a Postgres claim row (§2); because one pod serves one session, the pod is
directly addressable and the inner state never needs to leave it.

#### How it works today (the monolith)

`TranscodeManager` (`MediaBrowser.MediaEncoding/Transcoding/TranscodeManager.cs`) holds
`List<TranscodingJob> _activeTranscodingJobs` (`:48`) under a plain `lock`, plus an
`AsyncKeyedLocker<string>` keyed by output path (`:49`). A `TranscodingJob`
(`MediaBrowser.Controller/MediaEncoding/TranscodingJob.cs`) bundles three kinds of thing that the
monolith conflates and we must separate:

1. **Identity / lookup keys** — `PlaySessionId` (`:32`), `DeviceId` (`:72`), `LiveStreamId` (`:37`),
   `Id` (`:97`), `Type` (`:57`), `Path` (`:52`, the `MD5(mediaPath+UA+deviceId+playSessionId)`
   playlist path from §2), `MediaSource` (`:47`). Two lookup paths exist: by `playSessionId`
   (`GetTranscodingJob`, `:100`) and by `(path, type)` (`OnTranscodeBeginRequest`, `:688`).
2. **Live OS resources** — `Process` (`:62`, the ffmpeg handle), `CancellationTokenSource` (`:77`),
   `TranscodingThrottler` (`:137`), `TranscodingSegmentCleaner` (`:142`), and the scratch dir the
   segments are written to. None serializable.
3. **Refcount / liveness / observed progress** — `ActiveRequestCount` (`:67`), `LastPingDate`
   (`:147`), `PingTimeout` (`:152`), `IsUserPaused` (`:92`), `HasExited`/`ExitCode` (`:82`,`:87`),
   and the progress fields `CompletionPercentage`/`Framerate`/`BytesTranscoded`/`BitRate`/
   `TranscodingPositionTicks` (`:102`–`:127`).

The **lifecycle**: `StartFfMpeg` (`:371`) → `AcquireResources` (`:663`, opens the live stream and
buffers) → launches the `Process` → `OnTranscodeBeginning` (`:577`) creates the job with
`ActiveRequestCount = 1` and adds it to the list. Each further segment request that finds a live job
calls `OnTranscodeBeginRequest` (`:688`) to `++ActiveRequestCount` and cancel the kill timer;
`OnTranscodeEndRequest` (`:613`) does `--ActiveRequestCount` and, at zero, arms it. Process exit runs
`OnFfMpegProcessExited` (`:641`).

The **reaper** is the subtle part. HLS has no persistent connection — every segment is a separate
GET — so idle jobs are reaped by a keepalive timer, not by a closed socket. The client's playback
progress report drives it: `OnPlaybackProgress` (`:710`) → `PingTranscodingJob` (`:118`) refreshes
`LastPingDate` and re-arms a per-job kill timer (`PingTimer`, `:145`; 10 s progressive, 60 s HLS).
`OnTranscodeKillTimerStopped` (`:174`) kills the job once `now - LastPingDate ≥ PingTimeout`. The
explicit stop is `DELETE /Videos/ActiveEncodings` → `KillTranscodingJobs(deviceId, playSessionId)`
(`HlsSegmentController.cs:103`, `TranscodeManager.cs:194`).

Two **pod-local control loops** run per job: the `TranscodingThrottler` (`TranscodingThrottler.cs`)
ticks every 5 s and writes `p`/`c` (pause) or `u`/newline (resume) to ffmpeg **stdin** to stop it
racing too far ahead of the playhead; the `TranscodingSegmentCleaner` deletes segments behind the
playhead. Both need the `Process` stdin and the scratch dir. Finally `ReportTranscodingProgress`
(`:323`) pushes a `TranscodingInfo` into `SessionManager` so `GET /Sessions` can show encode state.

#### Relocation, per mechanism

The dividing question for each mechanism is CNPG's: is this *shape/lifecycle* (→ the CR) or is it
*the running workload* (→ the pod)? Almost everything is the workload.

| Mechanism | Today | New home | Why |
|:--|:--|:--|:--|
| Session shape + identity (`playSessionId`, `deviceId`, item/`mediaSource`, resolved argv, hwaccel class, output container) | fields in the in-process list | **`TranscodeSession` CR `spec`**, minted by the control plane at playback start, written once | This is the durable *shape* the operator reconciles — the CNPG `Cluster` object. It survives pod crashes and is the session's identity. |
| The running job itself | an entry in `_activeTranscodingJobs` | **one dedicated pod** the operator materializes from the CR (+ its scratch `PVC`) | CNPG `Cluster` → `StatefulSet` + `PVC`; here CR → pod. The pod *is* the session. |
| `Process`, `CancellationTokenSource`, throttler, segment cleaner, scratch dir (`:62,77,137,142`) | in-process | **pod-local, in the session's pod** | OS handles and stdin pipes — the "rows," not the "shape." Never serialized, never in etcd. |
| `ActiveRequestCount` (`:67`) | in-process refcount | **pod-local, in-memory** | The pod is dedicated to one session, so its local count *is* the session's count. Nothing to share. |
| Keepalive `LastPingDate`/`PingTimeout`/`IsUserPaused` (`:147,152,92`) | in-process, pinged by `OnPlaybackProgress` | **pod-local, in-memory** — the ping is affinity-routed straight to the session's pod (§2), exactly like a segment request | This is the change the pod-per-session model buys: the pod is directly addressable, so the ping reaches it and updates in-memory state as in the monolith. No claim row, no etcd write, no plane-to-plane RPC. |
| Idle reaping (`OnTranscodeKillTimerStopped`, `:174`) | per-job in-process timer | **pod-local timer; the pod exits when idle** | The reaper ports verbatim and manifests to Kubernetes as a graceful pod exit, which the operator turns into a CR delete. The control plane never computes liveness. |
| Explicit stop (`DELETE /Videos/ActiveEncodings`) | `KillTranscodingJobs` over the list | affinity-routed to the session's pod → `SIGTERM` ffmpeg → exit (or control plane deletes the CR → `ownerReference`/`preStop` kills the pod) | The request carries `playSessionId`; it reaches the one pod that is the session. |
| Observed progress (`ReportTranscodingProgress`, `:323`) | pushed into `SessionManager` in-process | **stays in the pod, exposed on a status endpoint**; `GET /Sessions` reads it on-demand from the pod | Querying the DB for its state, not mirroring every metric into the `Cluster` CR. Keeps progress out of both etcd and Postgres. |
| Segment files | scratch dir | **pod-local scratch `PVC`, dies with the pod** | Pod == session, so when the session ends the scratch is gone with it — no cross-pod GC, no cluster `Job` deleting a live pod's dir. |
| Session → pod routing (affinity, §2) | not applicable (one process) | **operator-maintained endpoint** (the CNPG `-rw` Service analog), rewritten only when the pod is created/recreated | The single low-write mapping the ingress reads; not a per-request table. |

The net: the CR holds **shape + lifecycle only** (create and delete — two writes); the pod holds
**every mechanism** (process, refcount, keepalive, throttle, progress, scratch); pings and segments
and progress **never leave the pod**; and the only externally visible low-write facts are the CR's
existence and its endpoint. etcd sees ≈ two writes per session; Postgres is out of the transcode hot
path entirely. `TranscodeSession` is also the one CR the *control plane* mints at runtime rather than
an admin declaring it — the `CertificateRequest` to the other CRDs' `Certificate`s (see §6).

#### The operator is a dumb shape-reconciler

Because all the mechanics live in the pod, the controller does nothing but ensure a pod exists,
recover from crashes, and clean up on graceful exit — exactly a CNPG-style reconcile-shape-and-recover
loop, never a liveness poller:

```go
func (r *Reconciler) Reconcile(ctx, req) (Result, error) {
    ts, err := r.Get(...)
    if apierrors.IsNotFound(err)      { return Result{}, nil }   // GC'd
    if !ts.DeletionTimestamp.IsZero() { return Result{}, nil }   // ownerRef/preStop kills the pod

    switch pod := r.podFor(ts); {
    case pod == nil:          r.Create(ownedPod(ts))   // materialize one pod from the shape
    case pod.idleExited():    r.Delete(ctx, ts)        // pod signalled "session over" -> delete CR
    case pod.crashed():       r.Delete(ctx, pod)       // recreate next loop; CR (identity) survives
    default:                  /* Running: nothing to do — the pod owns everything */
    }
    return Result{}, nil
}
```

#### Crash and takeover

A pod that dies loses its `Process` objects but not its CR — the CR is the durable identity, exactly
as a CNPG instance pod is disposable over a durable cluster object. The operator sees the pod gone and
recreates it for the still-live CR; the new pod restarts ffmpeg from the requested segment, which the
monolith already tolerates (`GetDynamicSegment` restarts whenever `currentTranscodingIndex` is null or
the requested segment is too far from it, `DynamicHlsController.cs:1478-1519`). The client, meanwhile,
is routing to the same operator-maintained endpoint, which now points at the new pod. Graceful idle is
the mirror image: the pod's own reaper ends ffmpeg, the pod exits 0, and the operator deletes the CR.
This is strictly better than the monolith, which loses every in-flight job on restart.

#### The one place the CNPG analogy strains: cardinality

CNPG clusters are *tens* of objects living for *months*; transcode sessions are *thousands* living
for *minutes*. Each individual CR is still low-write (create + delete — that is what keeps etcd safe),
but the *object churn* — create/delete rate and total count — stresses a dimension CNPG never
exercises. The saving grace is physical: concurrent transcodes are hard-capped by **GPU encode slots**
(NVENC/VAAPI session limits), so live-CR count is bounded by encode capacity — hundreds to low
thousands per cluster, not millions — which keeps per-session CRs tenable. This is the thing to
load-test before committing; if the churn proves too high, the fallback is to move the CR up a level
(the long-lived object is the `TranscodePool`, and sessions become bare pods tracked in a registry,
with no per-session CR). Separately, a fresh pod per session adds schedule + container-start latency to
first-segment TTFB; mitigate with a **warm pool** of pre-started pods that are assigned to a session
on demand rather than cold-started.

---

## 6. Scope

### In scope — the operation set

279 operations (`docs/analysis/02-plane-assignment.md`): 251 control, 24 transcode-pinned, 4
transcode-cacheable. Concretely, the capability set is:

- **Auth & users**: login (including the deprecated `{userId}/Authenticate` form older clients call),
  API keys, quick connect, user CRUD, user policy, user views.
- **Library reads**: `GET /Items` (88 params), item detail, `/Items/{id}/PlaybackInfo`, resume,
  latest, next-up, seasons/episodes, artists/albums/songs, genres, studios, persons, years, search
  hints, suggestions, filters.
- **User data & playstate**: mark played/unplayed, favorites, ratings, playback progress
  start/stop/ping — including all the hidden deprecated `Users/{userId}/...` route forms
  (`docs/analysis/01-route-inventory.md`).
- **Playback negotiation**: `POST /Items/{id}/PlaybackInfo` (the plane boundary), `LiveStreams`
  open/close, bitrate test.
- **Streaming (transcode plane)**: progressive `/Videos/{id}/stream`, `/Audio/{id}/stream`,
  `/Audio/{id}/universal`; HLS master/main/variant playlists and segments (both the current
  `hls1/` and legacy `hls/` forms); `DELETE /Videos/ActiveEncodings`.
- **Images**: item/artist/genre/person/studio/user images (read + write), all the hidden
  `Users/{userId}/Images/...` legacy forms. Control plane (Skia, not ffmpeg).
- **Subtitles & trickplay & attachments**: subtitle upload/delete/search/download (control),
  subtitle stream extraction (transcode-cacheable), trickplay tiles (control),
  attachment extraction (transcode-cacheable).
- **Sessions**: session list, capabilities, remote-control command relay, playstate relay.
- **Media segments** (intro/credit markers, `GET /MediaSegments/{id}`).
- **System**: `/System/Info`, `/System/Info/Public`, `/System/Ping`, localization, branding config
  (the JSON, not the web CSS).

### Explicit non-goals

Not built, deliberately. Roughly a third of the API surface, 140 operations (the `OUT` plane).

- **LiveTv** (`LiveTvController`, guide, channels, recordings)
- **SyncPlay** (`SyncPlayController`, `TimeSyncController`)
- **Plugins** (`PluginsController`, `PackageController`)
- **Channels** (`ChannelsController`)
- **Lyrics** (`LyricsController`)
- **Instant mix** (`InstantMixController`)
- **DLNA** (already removed as a controller upstream; profiles remain as data only)
- **Books, photos** (item types not served)
- **jellyfin-web** and everything that exists only to serve it: `DashboardController`,
  `StartupController` (first-run wizard), `BrandingController` CSS/splashscreen,
  `ConfigurationController` web config surface, `ActivityLogController`, `EnvironmentController`
  (filesystem browser), `BackupController`, `LibraryStructureController`,
  `ScheduledTasksController` (its recurring/ad-hoc task surface becomes the `ScheduledTask` /
  `TaskRun` CRDs in §6, not this HTTP controller).

There is no web UI. Native clients are the only consumers. Admin is CLI and CRDs, specified next.

### Admin surface: CRDs and CLI

The dividing line is **spec versus status, not CRD versus not.** A thing belongs in a CRD when it
has a non-trivial **admin-owned declarative half** — an identity and policy an administrator
declares and expects the cluster to converge to — *even when it also carries runtime state*. Having
runtime state is not disqualifying; you split it along the standard Kubernetes subresource seam:

- **`spec`** — admin desired-state: identity, policy, enablement. The reconciler writes it; the
  server reads it.
- **`status`** — a bounded, regenerable summary the server observes and writes back. The server
  writes it; the reconciler reads it. Two writers, two fields, no conflict — this is exactly how a
  `Pod` works (user writes spec, kubelet writes status).
- **Primary high-write runtime data** — playback positions, watch history, session rows, transcode
  claims — stays in **Postgres, never etcd**. It is high-frequency, unbounded, must be
  queried/joined/paginated, and is the system of record rather than observed state. `status`
  summarizes it; it does not hold it.

A thing is **Postgres-only** when it has *no* meaningful declarative half: it self-registers at
runtime, is high-cardinality and churning, or is primary content discovered rather than declared.

The last refinement generalized the reconciler's output: a CRD need not project into a Postgres row
— it can **materialize a Kubernetes object** (`ScheduledTask` → `CronJob`). Re-scanning every model
with that as an explicit second question — *is there admin desired-state that should become a K8s
workload?* — surfaces one resource the first passes missed (`TranscodePool`) alongside the task
pair. Applying the full lens yields **seven core custom resources across the reconciler's two output
modes**, plus two optional admin-side templates and four candidates the lens rejects (all recorded
below). An **eighth CR is different in kind**: `TranscodeSession` (§5) is minted by the *control
plane* at playback time, not declared by an admin — the runtime-workload analog of these config
objects, a `CertificateRequest` to their `Certificate`s. It is listed here for completeness but its
design lives in §5.

| Entity | Admin-owned declarative half | Home |
|:--|:--|:--|
| Library structure + options | paths, providers, scan policy | **`MediaLibrary`** CRD → Postgres |
| Server + transcode policy | allowed hwaccel, defaults, sinks | **`JellyfinServer`** CRD → Postgres |
| User identity + policy | username, roles, enablement, parental/access policy | **`User`** CRD (spec) + Postgres (runtime) |
| API integration key | named integration, enablement | **`ApiKey`** CRD (spec) + `Secret` (token) |
| Recurring task | task type, target, trigger, concurrency | **`ScheduledTask`** CRD → `CronJob`/`Job` |
| Ad-hoc task run | task type, target | **`TaskRun`** CRD → `Job` |
| Transcode capacity | hwaccel pool, node placement, scratch, autoscale | **`TranscodePool`** CRD → `Deployment`/HPA/PDB/PVC |
| Transcode session (runtime) | n/a — control-plane-minted, not admin-declared | **`TranscodeSession`** CR → one pod (§5) |
| Items / media sources / streams | none — scanner-discovered | Postgres |
| Playback & user data (`user_item_data`) | none — primary high-write | Postgres |
| Playback sessions, live-stream handles | none — runtime, no declarative half | Postgres |
| Devices + capabilities | none — self-register, client-posted | Postgres |
| Playlists, collections | none — user-created content | Postgres |

**`MediaLibrary`** (namespaced). Replaces `LibraryStructureController` and the library-options half
of `ConfigurationController`, both of which are out of scope as HTTP surfaces precisely because
they become declarative. One CR per library. Spec shape:

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: MediaLibrary
metadata: { name: movies }
spec:
  contentType: movies            # movies | tvshows | music | mixed
  paths:
    - /media/movies
  metadata:
    preferredLanguage: en
    countryCode: US
    providers: [tmdb, omdb]       # ordered; identity of providers, not their secrets
  images:
    enabled: true
    providers: [tmdb, fanarttv]
  trickplay:
    enabled: true
    hardwareAcceleration: false   # opt a library out of GPU trickplay generation
  scanSchedule: "0 3 * * *"       # informs the RefreshLibrary CronJob for this library
status:
  lastScan: <timestamp>
  itemCount: <int>
  conditions: [...]               # standard K8s conditions; surfaces scan/reconcile errors
```

An operator reconciles a `MediaLibrary` into the `library` rows in Postgres and (re)configures the
per-library scan CronJob (`docs/analysis/05-scheduled-tasks.md`). `status` is written back so
`kubectl get medialibrary` shows real scan state. Provider **credentials** are referenced by
`secretRef`, never inlined — the CR names which providers, a `Secret` holds their API keys.

**`JellyfinServer`** (namespaced, singleton per instance). Replaces the server-wide half of
`ConfigurationController`. Cluster-scoped-in-spirit settings that are not per-library: default
transcode settings, hardware-acceleration policy (which `HardwareAccelerationType` the transcode
plane may use, throttling, segment TTL), network exposure, and the analytics/observability sinks
from §8. Its transcode block is the operator-facing knob that the transcode-plane pods read.

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: JellyfinServer
metadata: { name: default }
spec:
  transcoding:
    hardwareAccelerationType: nvenc        # maps to MediaBrowser.Model.Entities.HardwareAccelerationType
    allowedCodecs: [h264, hevc, av1]
    throttle: true
    segmentTtlSeconds: 3600
  playback:
    defaultMaxStreamingBitrate: 120000000
  observability:
    decisionEventSink: otlp://...          # the playback-decision stream from §8
status:
  observedHardwareAcceleration: [nvenc]    # what the transcode nodes actually detected
  conditions: [...]                         # diverges from spec if allowed != available
```

Its `status` is the spec/status seam applied to the server: `spec.transcoding.hardwareAccelerationType`
is what the admin *allows*, `status.observedHardwareAcceleration` is what the transcode nodes report
*available*. When they diverge (admin asked `nvenc`, nodes probed none) that surfaces in
`status`/`conditions` instead of failing silently — the §8 correctness ethos applied to config.

**`User`** (namespaced). This is the resource the spec/status seam rescues. Its declarative half —
who the user is and what they may do — is admin desired-state; its runtime half — watch history,
positions, live credential — is not. Split accordingly:

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: User
metadata: { name: alice }
spec:
  username: alice
  enabled: true
  policy:
    isAdministrator: false
    enabledLibraries: [movies, tvshows]    # references MediaLibrary names
    maxParentalRating: 13
    accessSchedules: [...]
    sessionLimit: 3
  initialCredentialSecretRef:              # optional; read once at creation, never rewritten
    name: alice-initial-password
status:
  lastLogin: <timestamp>
  activeSessions: <int>                     # bounded observed summary, not the session rows
  conditions: [...]
```

The reconciler projects `spec` into the identity/policy columns of `app_user` (§5). Everything the
user *does* — `user_item_data` (positions, favorites, watch history), self-service password changes
— goes through the API into Postgres and **never touches the CR**: `initialCredentialSecretRef` is
consumed once to seed the first password, after which the live credential is Postgres-owned. The
first admin is now simply a `User` CR with `isAdministrator: true` — cleaner than the earlier
Secret-only bootstrap.

**`ApiKey`** (namespaced). A named integration credential (an *arr app, a script) is textbook
declarative admin config: low-cardinality, long-lived, GitOps-friendly. The admin declares the
integration; the reconciler generates the token and publishes it to a `Secret`, so key material is
never inlined in the CR or handled by the admin.

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: ApiKey
metadata: { name: sonarr }
spec:
  appName: Sonarr
  enabled: true
status:
  secretRef: { name: jellyfin-apikey-sonarr }   # reconciler-generated token lands here
  lastUsed: <timestamp>
  conditions: [...]
```

**Still Postgres-only, and why (the lens rejecting the rest):**

- **Playback & user data** (`user_item_data`) — primary, high-write (a progress ping every few
  seconds per stream), must be queried for resume/next-up. The `User` CR's `status` summarizes it;
  it cannot live in etcd.
- **Playback sessions, live-stream handles** — ephemeral, per-connection runtime with no declarative
  half. (The *transcode* session is the exception the CNPG shape carves out — it becomes a
  `TranscodeSession` CR whose pod holds all the runtime state; see §5. Its identity is durable enough
  to be a CR; its inner state still never touches etcd.)
- **Devices & capabilities** — self-register at runtime, high-cardinality, client-posted. (Admin
  policy over a device — enable/block — is thin; if it grows it attaches to the owning `User`, not
  a `Device` CR of its own.)
- **Items, media sources, streams** — discovered by the scanner from disk, not declared. The
  *library* is declared (`MediaLibrary`); its contents are found.
- **Playlists & collections** — user-created content, mutated constantly, queried and joined.
  Content, not config.

### Tasks: domain CRDs the reconciler materializes into Jobs

The four resources above are the reconciler's *first* output mode — it writes Postgres rows and
`Secret`s. Scheduled and ad-hoc tasks are its *second* mode: the CR is an app-domain task
definition, and the reconciler **spawns a Kubernetes `CronJob` or `Job` from it**, owning that
workload object by `ownerReference` so it is garbage-collected with the CR.

An earlier draft said tasks should be bare `CronJob`s and a CRD "would add nothing." That was wrong.
A domain CRD adds four things a raw `CronJob` cannot express:

1. **Interval-from-completion semantics.** `docs/analysis/05` flags that Jellyfin's `IntervalTrigger`
   measures from last *completion* while a `CronJob` is wall-clock. A `ScheduledTask` reconciler
   watches the prior `Job` finish and schedules the next itself — implementing the semantics rather
   than approximating them with `concurrencyPolicy: Forbid`.
2. **Typed domain targets.** `taskType` is an enum over the ported `IScheduledTask` set
   (`docs/analysis/05`), and targets are CR references (`libraryRef`) validated against
   `MediaLibrary` — not an opaque container command.
3. **A kubectl-native ad-hoc path.** A `TaskRun` CR replaces the out-of-scope
   `POST /ScheduledTasks/Running/{taskId}` we dropped with `ScheduledTasksController` — "scan this
   library now" without reviving a web-oriented HTTP surface.
4. **Cross-run `status`.** Last result, next run, active count — the spec/status seam again.

**`ScheduledTask`** (recurring). Reconciler → `CronJob` for wall-clock triggers, or self-scheduled
`Job`s for interval-from-completion triggers.

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: ScheduledTask
metadata: { name: nightly-movie-scan }
spec:
  taskType: RefreshLibrary          # enum over the ported IScheduledTask set (docs/analysis/05)
  target: { libraryRef: movies }    # validated against a MediaLibrary CR
  trigger:
    interval: 24h                   # from last completion; reconciler self-schedules
    # or: schedule: "0 3 * * *"     # wall-clock; reconciler emits a CronJob
  concurrencyPolicy: Forbid         # never overlap a long scan
status:
  lastRun: <timestamp>
  lastResult: Succeeded
  nextRun: <timestamp>
  active: 0
```

**`TaskRun`** (one-shot, ad-hoc/manual). Reconciler → a single `Job`; `kubectl create -f run.yaml`
or `jellyfinctl task run refresh-library --library movies`.

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: TaskRun
metadata: { name: scan-movies-now }
spec:
  taskType: RefreshLibrary
  target: { libraryRef: movies }
status:
  jobRef: { name: jellyfin-taskrun-scan-movies-now }
  phase: Running                    # Pending | Running | Succeeded | Failed
```

Not every task becomes a `ScheduledTask`. The three **pod-local GC** tasks from `docs/analysis/05`
(transcode/cache cleanup) stay pod-local goroutines scoped to a pod's own scratch volume — a
cluster-level `Job` deleting another live pod's scratch dir is exactly the failure that analysis
warns against. `ScheduledTask` is for cluster-level work (library scan, people validation, chapter
and trickplay images, subtitle/segment extraction); pod-local GC is not a CRD.

### Transcode capacity: `TranscodePool`, the workload the lens catches

The workload output mode is the natural home for the transcode plane's *substrate*. The plane's
shape is admin desired-state: which GPU node pool, which `HardwareAccelerationType`, the per-session
scratch template, and how much warm capacity to keep ready. `TranscodePool` is that declaration; the
per-session `TranscodeSession` pods (§5) are *scheduled onto* it.

```yaml
apiVersion: jellyfin.io/v1alpha1
kind: TranscodePool
metadata: { name: nvidia }
spec:
  hardwareAccelerationType: nvenc      # must be in JellyfinServer.spec's allowed set
  nodeSelector: { gpu: nvidia }
  scratch: { size: 100Gi, storageClass: fast-local }   # per-session PVC template
  warmPool: 2                          # pre-started idle pods that hide cold-start TTFB (§5)
  maxConcurrentSessions: 12            # the GPU encode-slot cap; bounds live TranscodeSession pods
status:
  readyWarmPods: 2
  activeSessions: 7                     # count of live TranscodeSession pods in this pool
  conditions: [...]                     # e.g. hwaccel not available on matched nodes
```

The reconciler maintains the warm pool (a small `Deployment` of idle, pre-started pods a new session
is promoted from instead of cold-starting), enforces `maxConcurrentSessions` against GPU encode
slots, and lets pending session pods drive node autoscaling (cluster-autoscaler / Karpenter). Three
wins over a bare Helm chart: `spec.hardwareAccelerationType` is validated against `JellyfinServer`'s
allowed set with the mismatch surfaced in `status`; the warm-pool buffer is the concrete cold-start
mitigation §5 calls for; and one CR per pool expresses **heterogeneous** clusters (an `nvenc` pool
and a `vaapi` pool with different node selectors and caps) cleanly. This replaces an earlier framing
in which `TranscodePool` was a `Deployment` of multi-tenant workers autoscaled on encodes-per-pod;
the pod-per-session model (§5) makes it a capacity substrate instead, and encodes-per-pod is always
one.

### Optional admin-side templates (wire-invisible)

Two further CRDs are defensible as *conveniences* that expand into spec already defined above. Both
are optional and neither changes the wire:

- **`MetadataProvider`** — a shared provider registry (`type`, `secretRef`, rate limit, enable) that
  `MediaLibrary` references by name, replacing per-library provider lists plus scattered `Secret`s
  and giving each provider observable `status` (quota, last error). Worth it because credentials and
  rate limits are server-wide, not per-library; skip it only when a deployment truly has one
  provider.
- **`Role`** — an admin-side policy template `User.spec.policy` may reference; the reconciler expands
  it into the per-user `app_user.policy` columns. It must stay **strictly wire-invisible** — if it
  ever reaches the API it becomes a redesign of Jellyfin's per-user policy model, which the
  transliterate-don't-redesign rule (§0) forbids. Pure convenience for managing many users alike.

### Considered and rejected

The lens is disciplined, not maximal. Four plausible-looking candidates are *not* CRDs:

- **Control plane as a CRD** — it has no domain shape beyond replica bounds. A stock `Deployment` +
  KEDA scaler in the chart (or a field on `JellyfinServer`) covers it; a CRD would wrap nothing.
- **A routing / `Ingress` CRD** — the plane-split rules (§2) are *derived from the fixed route
  inventory*, not admin-tuned. Ship them as generated static `HTTPRoute`/Envoy config, regenerated
  when the route inventory changes — an admin never edits them, so they are not desired-state.
- **A backup CRD** — the store is Postgres; backup belongs to the Postgres operator's own
  `Backup`/`ScheduledBackup` CRD (CloudNativePG et al.), not ours. Delegated, not rebuilt.
- **Media-volume `PVC`s** — media is pre-provisioned infrastructure (NFS, existing PVs) that
  `MediaLibrary.spec.paths` mount. Provisioning it is cluster-admin, not the Jellyfin reconciler.

The reconciler (a controller in `deploy/`) watches all seven core CRDs across its two output modes.
It is the **sole writer** of the spec-derived Postgres columns (library structure, server config,
user identity/policy, API-key identity) and their `Secret`s, *and* the owner of the Kubernetes
workloads the other CRDs materialize — `CronJob`/`Job` for `ScheduledTask`/`TaskRun`, and
`Deployment`/HPA/PDB/`PVC` for `TranscodePool` — each held by `ownerReference` so it is
garbage-collected with its CR. The server owns every `status` subresource and all runtime tables.
That keeps one source of truth per field: the API serves spec-derived data read-only, the
reconciler never touches runtime data, and no workload is hand-managed with `kubectl apply`.
The eighth CR, the control-plane-minted `TranscodeSession`, is driven by its own dumb shape-reconciler
(§5), separate from this config reconciler. Building both is Phase 5 work (§7).

---

## 7. Phasing and verification gates

Each phase states what *proves* it done. Gates, not schedules. A phase is not complete until its gate
is green in CI.

### Phase 0 — Harness before code

Build the capture harness and replay runner (§3) and the differential harness (§4) against the oracle
submodule. No Go server logic yet.

**Gate:** The differential harness runs the C# side against *itself* (oracle vs oracle) and produces
zero diffs across the full corpus — proving the harness plumbing, the synthetic capability injection,
and the argv-capture protocol are sound. The capture proxy records a full session from at least one
real client and the recording replays against the *oracle* with zero normalized diff — proving the
normalization rules are correct before any Go code exists to test.

### Phase 1 — Control plane read path

Auth, users, library reads, `GET /Items`, item detail, user data. No playback, no transcode.

**Gate:** Conformance (§3) green for the read-only subset of every captured client family — login,
browse, resume-list, item detail — with zero normalized diff. This is the first proof the data model
(§5) projects `BaseItemDto` correctly.

### Phase 2 — Playback negotiation (StreamBuilder)

`POST /Items/{id}/PlaybackInfo` and the `StreamBuilder` transliteration.

**Gate:** The `StreamBuilder` half of the differential harness (§4) is green across the full corpus —
identical `StreamInfo` and `TranscodeReasons` for every `(DeviceProfile, MediaSourceInfo)` pair,
including the dead-code `GreaterThanEqual` behaviour (`docs/analysis/03`). *And* conformance replay of
captured `PlaybackInfo` exchanges is zero-diff for every client family. This gate proves we negotiate
the same play method the oracle does — the correctness property that, if wrong, silently transcodes
what should direct-play (§8).

### Phase 3 — EncodingHelper (argv) and the transcode plane

`EncodingHelper` transliteration; progressive + HLS streaming; the pinned transcode plane with
Postgres claims and ingress affinity (§2).

**Gate (argv):** The `EncodingHelper` half of the differential harness green across the full corpus —
identical tokenized ffmpeg argv. This is the highest-risk gate; §9 defines its stop signal.
**Gate (streaming):** Captured playback sessions (direct play, direct stream, transcode, seek,
subtitle toggle) from every client family replay zero-diff, *and* segments actually play end-to-end
against the Go transcode plane in a cluster with ≥2 transcode pods, proving affinity keeps a session
on one pod across a rehash.

### Phase 4 — Remaining control surface

Images, subtitles, trickplay, attachments, sessions/remote-control, search, suggestions, media
segments, system info.

**Gate:** Conformance green for **100% of captured exchanges** across all five client families. This
is the definition of done for the server: every request five real clients make, replayed, zero
normalized diff.

### Phase 5 — Kubernetes operationalization

The seven config CRDs and their reconciler (§6) — four config/identity resources plus the
`ScheduledTask` / `TaskRun` / `TranscodePool` workload trio (`docs/analysis/05`) — plus the
control-plane-minted `TranscodeSession` CR and its shape-reconciler (§5); scale-to-zero / hibernation
of the control plane (and of `TranscodePool` at `minReplicas: 0`), transcode-pod disposal and
reconciliation, and pod-local GC for transcode scratch.

**Gate:** Control plane scales 0→N→0 with a captured session surviving a cold start; a transcode pod
killed mid-session is reconciled — the operator recreates the session's pod, which resumes from the
requested segment (§5) — or fails cleanly to a client-visible restart that the oracle also exhibits
under equivalent process death.

---

## 8. Observability of correctness

Incorrect `StreamBuilder` behaviour does not throw. It silently transcodes something that should have
direct-played — burning a GPU slot and degrading quality with no error anywhere. This must be
designed in from the start, not bolted on.

### Every playback emits its decision, not just its outcome

At the moment `StreamBuilder` returns, the control plane emits a structured **playback decision
event** — one per `PlaybackInfo` negotiation — carrying:

```
play_session_id
client            # family + version, from User-Agent / X-Emby-Authorization
item_id
source_container            chosen_container
source_video_codec          chosen_video_codec
source_audio_codec          chosen_audio_codec
play_method       # DirectPlay | DirectStream | Transcode
sub_protocol      # http | hls
transcode_reasons # the decoded bitfield, as a list of reason names
subtitle_method   # Encode | Embed | External | Hls | Drop | none
is_eligible_direct_play    is_eligible_direct_stream     # the two booleans from :711
bitrate_limit_exceeded                                   # :709
```

`transcode_reasons` is the load-bearing field. It is the decoded `TranscodeReason` bitfield
(`docs/analysis/03`), so every transcode carries a machine-readable *why*: `VideoCodecNotSupported`,
`ContainerBitrateExceedsLimit`, `SubtitleCodecNotSupported`, etc. A transcode with an empty or
surprising reason set is the signature of a StreamBuilder bug.

### The correctness signal is a metric, not a log line

Emit a counter `playback_decisions_total{play_method, transcode_reason, client, container_pair}`.
The alertable property is **a shift in the ratio**: if a client that historically direct-played a
codec pair starts transcoding it, the reason-labeled counter moves, and that is a correctness
regression even though nothing errored. This is the only way to catch silent mis-transcode in
production, and it is why the decision — not just the outcome — is emitted.

### Tie to the oracle

The decision event schema is identical to what the differential harness (§4) diffs. Production
telemetry and CI verification speak the same vocabulary: a `transcode_reasons` value that appears in
production but never in the corpus is a corpus gap; a reason the harness expects but production never
emits is a live-path bug. The two feed each other.

---

## 9. Risks

### The one that can sink the project: is HW-accel debugging convergent?

`EncodingHelper` is 7,987 lines producing ffmpeg argv across 10 pipelines multiplied by tonemapping
(5 availability predicates), deinterlace, subtitle burn-in, 5 driver-quirk booleans, and 4 ffmpeg
version gates (`docs/analysis/04`). The open question is whether, against a **fixed corpus**, argv
diffs *converge* (each fix reduces the diff set monotonically toward zero) or *diverge* (fixing one
driver's argv breaks another's, chasing a moving target forever).

**Why it might diverge:** the pipelines share helper functions. A change to a shared filter-string
builder to match VAAPI can perturb the QSV or NVIDIA output. The driver-quirk booleans interact
non-orthogonally (`docs/analysis/04` notes the 5 flags are "not independent").

**Why it should converge, if we hold the corpus fixed:** the differential harness (§4) makes both
sides pure functions of injected inputs with no host-hardware variance. Against a *frozen* corpus,
each argv token diff is a concrete, reproducible target. Transliteration — copying the C# branch
structure rather than re-deriving it — means a diff points at a specific mistranslated branch, not a
design flaw. Convergence is achievable **only** under strict transliteration and a frozen corpus.

**The stop signal.** Define convergence operationally: track `argv_token_diff_count` over the frozen
corpus per commit. Convergence means the count is **monotonically non-increasing** across a window of
fixes. The stop signal — the point at which we stop hand-fixing and escalate — is:

> Three consecutive fix commits, each of which reduces the diff on its targeted triple, fail to
> reduce (or increase) the **total** corpus diff count.

That pattern means fixes are trading one divergence for another: the code is not converging, and the
response is not "keep fixing" but "stop, and reduce corpus scope" — cut the pipeline/driver
combination that is thrashing to an explicit non-goal for the first release (e.g. ship NVIDIA + VAAPI
+ software, defer RKMPP), logged loudly per `docs/analysis`'s no-silent-caps rule. A narrower corpus
that provably converges beats a complete one that never does.

### Secondary risks

- **Spec-invisible endpoints.** 52 in-scope operations aren't in the published spec (§0). Mitigated
  by building to captured wire traffic, not the spec — but a client feature we never captured is a
  hole. Mitigation: capture broad real-client flows, and treat any production request that 404s as a
  capture gap to backfill.
- **`User-Agent` in the job key.** May fork ffmpeg jobs in ways our `playSessionId` affinity doesn't
  model (§2). Runtime experiment required before finalizing job identity.
- **Device capabilities were never persisted** (`docs/analysis/06`, `DeviceManager.cs:33`). If a real
  client relies on the server *forgetting* caps on restart, moving them to Postgres changes behaviour.
  Low probability, but on the flagged-experiment list (§ analysis 06).
- **`IntervalTrigger` vs CronJob semantics** (`docs/analysis/05`): last-completion spacing vs
  wall-clock. Mitigated by `concurrencyPolicy: Forbid`, but confirm interval semantics against the
  running oracle.
- **Casing duality.** The API serves both camelCase and PascalCase JSON. The differ handles it (§3),
  but the Go serializer must produce *both* on demand, keyed on the request's `Accept` media type.

### Runtime experiments outstanding (consolidated)

These need the real server running, which needs the .NET SDK absent from this session (§1):

1. Does any real client vary `User-Agent` within a play session? (§2, job identity)
2. Do real clients ever send `GreaterThanEqual` profile conditions? (§3 analysis, dead-code branch)
3. What do clients do when device capabilities are missing after a restart? (§5, §6)
4. Exact `IntervalTrigger` timing semantics for long-running tasks. (§5)
5. Confirm the `containerSupported` mutation-during-LINQ-enumeration ordering in
   `GetVideoDirectPlayProfile` holds as the analysis assumes. (`docs/analysis/03`)
