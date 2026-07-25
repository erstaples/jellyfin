# Manager coupling map

Every piece of in-process mutable state below is a thing that must relocate to Postgres, Redis, or
a pod-local scope before the server can run as more than one replica. This is the list.

## The blocking one

### TranscodeManager — `MediaBrowser.MediaEncoding/Transcoding/TranscodeManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_activeTranscodingJobs` | 48 | `List<TranscodingJob>` — every live ffmpeg job in the process |
| `_transcodingLocks` | 49 | `AsyncKeyedLocker<string>` keyed by output path |

This is the single fact the whole project turns on. A `TranscodingJob`
(`MediaBrowser.Controller/MediaEncoding/TranscodingJob.cs`) holds a live `Process` handle (`:62`),
a `CancellationTokenSource` (`:77`), a `TranscodingThrottler` (`:137`), a
`TranscodingSegmentCleaner` (`:142`), and an `ActiveRequestCount` (`:67`) plus `LastPingDate`
(`:147`) / `PingTimeout` (`:152`) used for liveness.

None of that is serialisable. The `Process` handle and the scratch dir are inherently
pod-local, which is why the transcode plane is pinned and its pods are individually disposable
rather than replicated.

**Lookup key.** Jobs are found by `playlistPath`, which is
`Path.ChangeExtension(state.OutputFilePath, ".m3u8")` where `OutputFilePath` is
`MD5(mediaPath + "-" + UserAgent + "-" + deviceId + "-" + playSessionId)`
(`Jellyfin.Api/Helpers/StreamingHelpers.cs:384`).

Two consequences:

1. `playlistId` in the segment route is **not** the key. `DynamicHlsController.cs:1420` emits the
   literal string `"hls1/main/"` as the segment URI prefix, and the parameter is annotated
   `CA1801:ReviewUnusedParameters` at `:1090`. It is always `main`.
2. `User-Agent` is part of the key. A client that varies its UA mid-session forks a second ffmpeg
   job. Preserve this or lose compatibility with whatever client depends on it — **flag for a
   runtime experiment.**

Relocation: the job registry becomes a Postgres table of *session → pod* claims. The `Process`
handle stays pod-local. The ingress routes by `playSessionId` query param to the claiming pod.

## Session and device state

### SessionManager — `Emby.Server.Implementations/Session/SessionManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_activeConnections` | 64 | `ConcurrentDictionary<string, SessionInfo>` |
| `_activeLiveStreamSessions` | 67 | `ConcurrentDictionary<string, ConcurrentDictionary<string, string>>` |

Session key is `appName + deviceId` (`:478`) — string concatenation with no separator, so
`("AbC","d")` and `("Ab","Cd")` collide. Reproduce the concatenation exactly.

`SessionInfo` carries the WebSocket controllers used for remote control (`/Sessions/{id}/Playing`
etc.). Relocation: session rows in Postgres; WebSocket fan-out via Redis pub/sub or Postgres
`LISTEN/NOTIFY`. Controllers depending on it: `SessionController`, `PlaystateController`,
`UserController` (token revocation, `UserController.cs:163`).

### DeviceManager — `Jellyfin.Server.Implementations/Devices/DeviceManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_capabilitiesMap` | 33 | `ConcurrentDictionary<string, ClientCapabilities>` |
| `_devices` | 34 | `ConcurrentDictionary<int, Device>` |
| `_deviceOptions` | 35 | `ConcurrentDictionary<string, DeviceOptions>` |

`_devices` and `_deviceOptions` are write-through caches over EF-backed tables — droppable.
`_capabilitiesMap` is **not persisted**: client capabilities posted to
`POST /Sessions/Capabilities/Full` live only in memory and are lost on restart. This must become a
Postgres table, because a client that posts capabilities once and then streams must find them
still there on a different pod.

Controllers depending on it: `DevicesController`, `SessionController`, and indirectly the entire
playback path (capabilities feed `DeviceProfile` resolution).

### MediaSourceManager — `Emby.Server.Implementations/Library/MediaSourceManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_openStreams` | 61 | `ConcurrentDictionary<string, ILiveStream>` |
| `_providers` | 65 | provider registry (static after startup) |

`_openStreams` backs `POST /LiveStreams/Open` / `Close` (`MediaInfoController.cs:269`, `:314`).
For non-LiveTv content this is used for the "open a stream, hold it, then play" flow. Relocation:
Postgres row keyed by `liveStreamId`, with the actual handle pod-local on the transcode plane.

## Caches — droppable, but behaviour-visible

### LibraryManager — `Emby.Server.Implementations/Library/LibraryManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_cache` | 89 | `FastConcurrentLru<Guid, BaseItem>`, sized from config (`:181`) |

A read-through LRU over items. Invalidated on write (`:597-600`). Safe to drop or replace with a
shared cache, but note that **stale reads are currently possible only within one process** — a
multi-replica deployment with per-pod caches would widen that window. Prefer no cache initially;
add one only when a measurement demands it.

### ProviderManager — `MediaBrowser.Providers/Manager/ProviderManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_activeRefreshes` | 65 | `ConcurrentDictionary<Guid, double>` — refresh progress by item |
| `_metadataProviderCache` | 82 | provider resolution cache |
| `_imageProviders` / `_metadataServices` / `_metadataProviders` / `_savers` / `_externalIds` / `_externalUrlProviders` | 84-89 | static registries populated at startup |

`_activeRefreshes` is progress state surfaced to clients via WebSocket
(`RefreshProgress` messages). It must move to Postgres or be dropped along with live refresh
progress reporting. The registries are static and become compile-time in Go.

### BaseConfigurationManager — `Emby.Server.Implementations/AppBase/BaseConfigurationManager.cs`

| State | Line | Contents |
|:--|--:|:--|
| `_configurations` | 22 | `ConcurrentDictionary<string, object>` |

Server configuration held in memory, persisted to XML on disk. Replaced by ConfigMap / CRD.

## Clean — no relocation needed

### UserManager — `Jellyfin.Server.Implementations/Users/UserManager.cs`

No in-process collections. Fully EF/DbContext-backed. This is the model the other managers should
have followed and the easiest to port.

## Summary of what must move

| Destination | State |
|:--|:--|
| **Postgres** | device capabilities, sessions, live-stream handles, transcode session→pod claims, refresh progress |
| **Redis or LISTEN/NOTIFY** | WebSocket fan-out for session/playstate/refresh messages |
| **Pod-local (transcode plane)** | ffmpeg `Process` handles, scratch dirs, throttlers, segment cleaners |
| **ConfigMap / CRD** | server configuration |
| **Deleted** | all read-through caches, all provider registries |

## Needs a runtime experiment

- Whether any real client varies `User-Agent` within a play session (would fork ffmpeg jobs).
- Whether `appName + deviceId` collisions occur in practice with real client identifiers.
- What clients do when `POST /Sessions/Capabilities/Full` data is missing — does playback still
  negotiate correctly, or do they assume server-side memory?
