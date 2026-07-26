# Differential harness contract

Specification for the harness that verifies the two highest-risk transliterations —
`StreamBuilder` (playback negotiation) and `EncodingHelper` (ffmpeg argv) — by feeding
identical inputs into the C# oracle and the Go port and diffing the outputs.

Design input: `docs/design/00-architecture.md` §4. Analysis inputs:
`docs/analysis/03-streambuilder-decision-tree.md`, `docs/analysis/04-encodinghelper-shape.md`.

Constraints, restated: **no media files, no GPU, runs in CI on every commit.** The oracle is
the C# source in this repo, pinned as a read-only submodule (§1 of the design doc). The
harness is a thin C# console app linked against it, speaking JSON over stdin/stdout, plus a
Go-side driver that feeds it the same corpus it feeds the port.

**Verification status.** The document was first drafted from source alone, with no SDK
available. The SDK has since been installed (`dotnet` 10.0.110 — see §7 for how) and the
claims that could be checked locally **have been executed**: the oracle test suite, the
serializer behaviour, the `DynamicHlsController` reflection route, the ambient host facts, the
`containerSupported` question, and an end-to-end argv build with a synthetic capability
profile and no ffmpeg, media, or GPU. Two source-only inferences turned out to be wrong and
are corrected in place (§2.2, and the `defaultPreset` note under Gate 5a). Steps still
requiring work in the Go repo's CI remain marked **[SDK]**.

---

## 0. Corrections to design doc §4

The design doc names the harness entry points as
`EncodingHelper.GetVideoArguments` and `StreamBuilder.BuildVideoItem`. Neither is usable as
named:

- **`EncodingHelper.GetVideoArguments` does not exist.** `GetVideoArguments` is a *private
  method on the API controller* — `Jellyfin.Api/Controllers/DynamicHlsController.cs:1783` —
  not on `EncodingHelper`.
- **`StreamBuilder.BuildVideoItem` is private** (`MediaBrowser.Model/Dlna/StreamBuilder.cs:646`).
  The public entry is `GetOptimalVideoStream` (`:230`), which wraps it with media-source
  selection and a sort (`:256-299`). Driving `BuildVideoItem` directly would skip
  `ValidateMediaOptions` (`:1667`) and `GetOptimalStream`'s ranking, both of which are
  wire-visible.

Corrected entry points are in §1. The larger consequence is §1.3: **the HLS argv is assembled
in the API controller, not in `EncodingHelper`**, which means the argv contract straddles the
plane boundary drawn in design doc §2.

---

## 1. Entry points

### 1.1 StreamBuilder — two public entries

| Entry | File:line | Signature |
|:--|:--|:--|
| `GetOptimalVideoStream` | `MediaBrowser.Model/Dlna/StreamBuilder.cs:230` | `StreamInfo? GetOptimalVideoStream(MediaOptions options)` |
| `GetOptimalAudioStream` | `MediaBrowser.Model/Dlna/StreamBuilder.cs:51` | `StreamInfo? GetOptimalAudioStream(MediaOptions options)` |

These are the only two public non-static instance methods that produce a `StreamInfo`. They
are the sole call sites from the API layer: `Jellyfin.Api/Helpers/MediaInfoHelper.cs:257-258`
dispatches on `item.MediaType == MediaType.Audio`.

A third public entry is worth exposing separately because the subtitle sub-decision is an
independent tree that already has dedicated upstream tests:

| Entry | File:line | Signature |
|:--|:--|:--|
| `GetSubtitleProfile` | `MediaBrowser.Model/Dlna/StreamBuilder.cs:1455` | `static SubtitleProfile GetSubtitleProfile(MediaSourceInfo, MediaStream, SubtitleProfile[], PlayMethod, ITranscoderSupport, string?, MediaStreamProtocol?)` |

**Construction.** `StreamBuilder(ITranscoderSupport transcoderSupport, ILogger logger)`
(`:40`). `ITranscoderSupport` (`MediaBrowser.Model/Dlna/ITranscoderSupport.cs:5-12`) is three
predicates — `CanEncodeToAudioCodec`, `CanEncodeToSubtitleCodec`, `CanExtractSubtitles`. All
three are injectable capability facts (§3.4). The logger is behaviourally inert; the harness
binds `NullLogger`.

**Input type: `MediaOptions`** (`MediaBrowser.Model/Dlna/MediaOptions.cs`, 9 lines of ctor
defaults + 16 settable members). The ctor (`:14-20`) sets `Context = Streaming`,
`EnableDirectPlay = true`, `EnableDirectStream = true`; the harness must reproduce these
defaults for any field the corpus omits. `Profile` is `required` (`:70`).
`GetMaxBitrate(bool isAudio)` (`:120`) is a pure method on the options object that reads
`Profile.MaxStaticBitrate` / `MaxStaticMusicBitrate` / `MaxStreamingBitrate` — transliterate
it, do not inline it.

Nested inputs:
- `DeviceProfile` (`MediaBrowser.Model/Dlna/DeviceProfile.cs`, 71 lines): 5 scalar bitrate
  caps with non-null defaults (`:30,35,40,45` — `8000000/8000000/128000/8000000`) plus the
  five arrays enumerated in `03-streambuilder-decision-tree.md`
  (`DirectPlayProfiles :50`, `TranscodingProfiles :55`, `ContainerProfiles :60`,
  `CodecProfiles :65`, `SubtitleProfiles :70`). **The defaults are load-bearing**: a corpus
  entry that omits `MaxStreamingBitrate` gets 8 Mbit, not unlimited.
- `MediaSourceInfo[]` (`MediaBrowser.Model/Dto/MediaSourceInfo.cs`, 46 settable members).
  Behaviour-relevant here: `Container :42`, `Bitrate :103`, `RunTimeTicks :56`,
  `Protocol :30`, `VideoType :91`, `SupportsDirectPlay :70`, `SupportsDirectStream :68`,
  `SupportsTranscoding :66`, `TranscodingContainer :115`, `MediaStreams :97`,
  `DefaultAudioIndexSource :123`, `DefaultAudioStreamIndex :125`,
  `DefaultSubtitleStreamIndex :127`.

**Output type: `StreamInfo`** (`MediaBrowser.Model/Dlna/StreamInfo.cs`, 1,395 lines) —
39 settable members and 25 computed properties. The diff surface is defined in §5.2.
Nullable: both entries return `null` when `MediaSources` is empty or the id filter matches
nothing.

**Error surface.** `ValidateMediaOptions` (`:1667`) throws `ArgumentException` for a null
`Profile` (`:1676`), null `MediaSources` (`:1681`), and — video path only — an
`AudioStreamIndex`/`SubtitleStreamIndex` without a `MediaSourceId` (`:1688`, `:1693`); plus
`ArgumentException.ThrowIfNullOrEmpty(options.DeviceId)` when `ItemId` is empty (`:1671`).
`GetOptimalAudioStream` additionally throws via
`ArgumentNullException.ThrowIfNull(audioStream)` (`:102`) when the source has no audio
stream. **Thrown exceptions are part of the contract** and must be represented in the
protocol (§2.4), not swallowed.

### 1.2 EncodingHelper — the argv-producing entries

`EncodingHelper` produces argv as a **single `string`**, not a token list. There are two
public whole-command-line methods:

| Entry | File:line | Signature |
|:--|:--|:--|
| `GetProgressiveVideoFullCommandLine` | `MediaBrowser.Controller/MediaEncoding/EncodingHelper.cs:7646` | `string GetProgressiveVideoFullCommandLine(EncodingJobInfo state, EncodingOptions encodingOptions, EncoderPreset defaultPreset)` |
| `GetProgressiveAudioFullCommandLine` | `MediaBrowser.Controller/MediaEncoding/EncodingHelper.cs:7836` | `string GetProgressiveAudioFullCommandLine(EncodingJobInfo state, EncodingOptions encodingOptions, string outputPath)` |

Call sites confirm these are the real entries:
`Jellyfin.Api/Controllers/VideosController.cs:485` (with `EncoderPreset.superfast`) and
`Jellyfin.Api/Helpers/AudioHelper.cs:147`.

The video method's format string (`:7666-7677`) shows the composition — nine sub-builders
whose outputs are concatenated:
`GetInputModifier` → `GetInputArgument` (`:1245`) → `GetMapArgs` →
`GetProgressiveVideoArguments` (`:7697`) → `-map_metadata -1 -map_chapters -1` →
`-threads {n}` → `GetProgressiveVideoAudioArguments` → `GetSubtitleEmbedArguments` →
format/movflags → `-y "{outputPath}"`.

### 1.3 The HLS argv lives in the API controller — plane-boundary problem

| Entry | File:line |
|:--|:--|
| `DynamicHlsController.GetCommandLineArguments` | `Jellyfin.Api/Controllers/DynamicHlsController.cs:1574` (**private**) |
| `DynamicHlsController.GetVideoArguments` | `Jellyfin.Api/Controllers/DynamicHlsController.cs:1783` (private) |
| `DynamicHlsController.GetAudioArguments` | `Jellyfin.Api/Controllers/DynamicHlsController.cs:1659` (private) |

`GetCommandLineArguments` calls into `EncodingHelper` for `GetVideoEncoder`,
`GetNumberOfThreads`, `GetMapArgs`, `GetInputModifier`, `GetInputArgument` (`:1576-1590`) but
owns the HLS muxer flags itself: `-hls_playlist_type`, `-hls_segment_type`,
`-hls_fmp4_init_filename`, `-hls_segment_filename`, `-hls_time`, `-start_number`,
`-hls_base_url`, `-max_muxing_queue_size` (`:1637-1651`). It also carries its own ffmpeg
version gates — `_minFFmpegFlacInMp4 = 6.0` (`:48`), `_minFFmpegX265BframeInFmp4 = 7.0.1`
(`:49`), `_minFFmpegHlsSegmentOptions = 5.0` (`:50`) — used at `:1606`, `:1676`, `:1862`.

Consequences the harness must absorb:

1. **HLS is the dominant real-world path** (every `HLS.mp4` row in
   `tests/Jellyfin.Model.Tests/Dlna/StreamBuilderTests.cs` ends here). Excluding it would
   leave the highest-traffic argv untested.
2. **Accessibility.** These are `private` on an MVC controller with a heavyweight ctor.
   Options, in preference order:
   - **(a)** Add `[assembly: InternalsVisibleTo]` + widen to `internal` in the pinned oracle.
     Rejected — the oracle is read-only by the §1 repo decision.
   - **(b)** Reflection (`BindingFlags.NonPublic | Instance`) against a
     `DynamicHlsController` instance constructed with mocked services. Fragile but requires
     zero oracle edits. **Recommended.**
   - **(c)** Copy the method body into the harness. Rejected — a copy is not an oracle.
   Choosing (b) means the harness must construct `DynamicHlsController` and mock its ctor
   dependencies. **Both halves verified against the compiled assembly.** There is exactly
   one constructor, taking 11 parameters:

   ```
   ILibraryManager libraryManager            IServerConfigurationManager serverConfigurationManager
   IUserManager userManager                  IMediaEncoder mediaEncoder
   IMediaSourceManager mediaSourceManager    IFileSystem fileSystem
   ITranscodeManager transcodeManager        ILogger<DynamicHlsController> logger
   DynamicHlsHelper dynamicHlsHelper         EncodingHelper encodingHelper
   IDynamicHlsPlaylistGenerator dynamicHlsPlaylistGenerator
   ```

   Nine are interfaces (mockable outright). Two are concrete classes — `DynamicHlsHelper`
   and `EncodingHelper` — and must be constructed for real; `EncodingHelper` is the one
   already built with the synthetic capability profile (§3.1), which is what makes the whole
   arrangement deterministic.

   `GetCommandLineArguments` resolves under
   `BindingFlags.NonPublic | BindingFlags.Instance` with signature
   `(String outputPath, StreamState state, Boolean isEventPlaylist, Int32 startNumber)` —
   matching `:1574`. Option (b) is confirmed viable.
3. **Go-side placement.** The design doc puts `DynamicHlsController` in the transcode plane
   and `PlaybackInfo` in the control plane. `GetCommandLineArguments` is transcode-plane code
   that lives in an API controller in C#; the Go port should relocate it into the
   argv-builder package. That relocation is invisible to the harness — it diffs strings — but
   should be recorded so the port doesn't accidentally reproduce the controller coupling.

### 1.4 Input types for the argv entries

**`EncodingJobInfo`** (`MediaBrowser.Controller/MediaEncoding/EncodingJobInfo.cs`, 735 lines).
Constructible standalone: `new EncodingJobInfo(TranscodingJobType jobType)` (`:28`) — this is
exactly what the upstream test does
(`tests/Jellyfin.Controller.Tests/MediaEncoding/EncodingHelperTests.cs:254`). ~40 settable
members plus computed ones. Behaviour-relevant settables:
`VideoStream :63`, `AudioStream :125`, `SubtitleStream :81`, `MediaSource :89`,
`OutputVideoCodec :69`, `OutputAudioCodec :77`, `OutputContainer :113`,
`OutputFilePath :97`, `SubtitleDeliveryMethod :83`, `SupportedAudioCodecs :127`,
`SupportedVideoCodecs :129`, `SupportedSubtitleCodecs :85`, `BaseRequest :135`,
`TranscodingType :139`, `IsVideoRequest :137`, `RunTimeTicks :93`, `VideoType :65`,
`InputProtocol :71`, `MediaPath :73`.

Computed properties that read through `MediaSource` and so cannot be set independently:
`IgnoreInputDts :101`, `IgnoreInputIndex :103`, `GenPtsInput :105`. Three are hardcoded
`false` — `DiscardCorruptFramesInput :107`, `EnableFastSeekInput :109`, `GenPtsOutput :111` —
which makes `GetOutputFFlags` (`EncodingHelper.cs:7681`) dead code that always returns empty.
**Transliterate the constant, keep the dead branch** (same class of hazard as
`ApplyTranscodingConditions`' `GreaterThanEqual` skip in `03`).

`state.User` is a `Jellyfin.Database` entity, but `EncodingHelper` reads it at exactly two
sites — `:7217` and `:7240`, both inside `TryStreamCopy` — and only to test two permissions:
`PermissionKind.EnableVideoPlaybackTranscoding` and
`PermissionKind.EnableAudioPlaybackTranscoding`. **The harness models `User` as a
two-boolean tri-state** (`null` / `{video:bool, audio:bool}`), not as a database entity.

**`StreamState`** (`MediaBrowser.Controller/Streaming/StreamState.cs`, 183 lines) extends
`EncodingJobInfo` (`:11`) and is what the HLS path takes. Its ctor needs
`IMediaSourceManager` and `ITranscodeManager` (`:23`), both mockable to no-ops for argv
purposes. It adds behaviour the harness must supply:
- `Request` (`:37`) — casts `BaseRequest` to `StreamingRequestDto`; the setter also sets
  `IsVideoRequest`.
- `SegmentLength` (`:73`) — **User-Agent sniffing.** Returns 6 for AppleTV/cfnetwork/ipad/
  iphone/ipod (`:84-92`), 3 for a segmented live stream (`:94-97`), 6 otherwise for copy
  codecs, 3 for non-copy. `UserAgent` (`:127`) is therefore a **corpus input**, and it
  reaches argv through `-hls_time` (`DynamicHlsController.cs:1644`).
- `MinSegments` (`:107`) — derived from `SegmentLength`.
- `IsOutputVideo` (`:69`) — `Request is VideoRequestDto`, so the *runtime type* of the
  request DTO is a protocol-visible fact, not just its fields.

**`EncodingOptions`** (`MediaBrowser.Model/Configuration/EncodingOptions.cs`, 313 lines,
49 settable properties) — the server's admin-configured encoding settings. Serialized whole
into the request. Notable gates read by the predicates in §3.2:
`HardwareAccelerationType`, `EnableTonemapping`, `EnableVppTonemapping`,
`EnableVideoToolboxTonemapping`, `HardwareDecodingCodecs`, `PreferSystemNativeHwDecoder`,
`EnableEnhancedNvdecDecoder`, `VaapiDevice`, `EncodingThreadCount`, `MaxMuxingQueueSize`,
`EnableAudioVbr`, `HlsAudioSeekStrategy`.

### 1.5 Output type for the argv entries

A single `string`. It is handed to
`ProcessStartInfo.Arguments` at
`MediaBrowser.MediaEncoding/Transcoding/TranscodeManager.cs:431`. **This is what makes
"tokenized argv" well-defined**: the tokenizer is .NET's `ProcessStartInfo.Arguments` parser,
which applies Windows-style quoting rules (`"` groups, `\"` escapes a quote, backslashes are
literal except before a quote) on *all* platforms. The Go side must not use `strings.Fields`
or a POSIX shell tokenizer. See §5.1.

---

## 2. The C#↔Go JSON protocol

### 2.1 Transport

A single console executable, `JellyfinOracle.Harness`, referencing `MediaBrowser.Model`,
`MediaBrowser.Controller`, `Jellyfin.Api`, and `MediaBrowser.MediaEncoding` from the pinned
submodule.

- **Framing:** newline-delimited JSON. One request object per line on stdin; one response
  object per line on stdout, in order. Requests carry an `id` echoed in the response, so the
  driver can pipeline.
- **Encoding:** UTF-8, no BOM. Responses are written with `WriteIndented = false`.
- **Lifecycle:** the process is long-lived; the driver writes the whole corpus and reads
  responses until EOF. One process invocation per CI run, not per case — process startup
  dominates otherwise.
- **stderr** is diagnostic only and never parsed.

The Go driver runs the same corpus through the Go implementation in-process and diffs
response objects field-by-field.

### 2.2 Serializer

The oracle side uses `JsonDefaults.Options`
(`src/Jellyfin.Extensions/Json/JsonDefaults.cs:29-48`) so the harness's understanding of
`DeviceProfile`/`MediaSourceInfo`/`StreamInfo` is byte-identical to the API's. Relevant
settings: `DefaultIgnoreCondition = WhenWritingNull`,
`NumberHandling = AllowReadingFromString`, `PropertyNamingPolicy = null` (PascalCase —
`Options` does **not** apply camelCase; that is the separate `CamelCaseOptions`).

This is the same loader the existing upstream corpus uses
(`tests/Jellyfin.Model.Tests/Dlna/StreamBuilderTests.cs:730`).

**Two distinct defects around `[Flags]` enums. Both verified by execution
(`dotnet` 10.0.110); the first is not what it looks like from source.**

**(a) `[JsonIgnore]` silently drops two load-bearing input fields.** The properties that
matter on the *input* side are annotated `[JsonIgnore]`:

- `MediaSourceInfo.TranscodeReasons` — `MediaSourceInfo.cs:118-119`
- `MediaSourceInfo.DefaultAudioIndexSource` — `MediaSourceInfo.cs:121-122`

so they are never written **and never read**. Confirmed empirically: serializing a
`MediaSourceInfo` with `DefaultAudioIndexSource = User | Language` through
`JsonDefaults.Options` emits no such key, and feeding
`{"DefaultAudioIndexSource":["User"]}` back deserializes to `None` **without raising
anything**.

`DefaultAudioIndexSource` is **load-bearing**: it narrows the candidate audio-stream set in
`BuildVideoItem` (`StreamBuilder.cs:670-707`, per `03-streambuilder-decision-tree.md` step 2).
So a corpus fixture cannot express it, and — worse than an exception — a fixture that tries
is **silently ignored**. Both implementations would then run with `None` and agree, producing
a false green over the entire audio-reselection branch set. The existing upstream fixtures
never set the field, so nothing upstream catches this.

A read-capable converter does **not** fix this; `[JsonIgnore]` is checked before converters
run. The harness must instead either (i) supply a custom `IJsonTypeInfoResolver` that clears
`ShouldSerialize`/re-enables `Set` for these two properties, or (ii) carry them as explicit
side-channel fields in the request envelope and assign them after deserialization. **(ii) is
recommended** — it needs no reflection into serializer internals and makes the override
visible in the corpus schema. §4.1's `mediaSourceOverlay` block exists for this.

**(b) `JsonFlagEnumConverter<T>.Read` genuinely throws — on the output type.**
`src/Jellyfin.Extensions/Json/Converters/JsonFlagEnumConverter.cs:18-20` throws
`NotImplementedException`; only `Write` is implemented, emitting an array of member-name
strings (`:23-35`), and the factory claims every `[Flags]` enum
(`JsonFlagEnumConverterFactory.cs:16-18`). Verified: deserializing `["ContainerNotSupported"]`
as a `TranscodeReason` through `JsonDefaults.Options` throws `NotImplementedException`.

A reflection sweep over the twelve input/output types finds exactly one `[Flags]`-typed
property that is *not* `[JsonIgnore]`d and therefore would hit `Read`:
**`StreamInfo.TranscodeReasons`** (`StreamInfo.cs:255`). That is the harness's **output**
type — so this bites the moment the driver deserializes a C# response into a `StreamInfo`,
or reloads a stored golden `StreamInfo` fixture.

**Resolution for (b):** the harness clones `JsonDefaults.Options` via the copy constructor,
removes the `JsonFlagEnumConverterFactory` instance, and inserts a read-capable replacement
whose `Write` is byte-identical to the original. **Verified working**: the clone accepts the
array-of-names form and a plain integer, and re-serializing the result reproduces the
original JSON exactly. Note the factory must be *removed*, not merely preceded — inserting
ahead of it leaves `Converters.Count` unchanged at 9 and the original still registered.

### 2.3 Operations

Four ops, dispatched on `"op"`.

```
op = "streambuilder.video" | "streambuilder.audio"
   | "encodinghelper.progressive" | "encodinghelper.hls"
```

**Request envelope (all ops):**

```jsonc
{
  "id": "corpus/chrome/mp4-h264-ac3-srt-2600k/intel-ihd/0001",  // opaque, echoed
  "op": "streambuilder.video",
  "capabilities": { /* §3 — required for encodinghelper.*, ignored for streambuilder.* */ },
  "transcoderSupport": {          // §3.4 — required for streambuilder.*
    "canEncodeToAudioCodec":    ["aac", "mp3", "ac3", "eac3", "flac", "opus"],
    "canEncodeToSubtitleCodec": ["srt", "ass", "ssa", "vtt"],
    "canExtractSubtitles":      ["srt", "ass", "ssa", "pgssub", "dvdsub", "vtt"]
  },
  "input": { /* per-op, below */ }
}
```

`transcoderSupport` is expressed as three allowlists, not as booleans, because the C#
interface is `bool f(string codec)`; the harness binds a lambda that tests membership
(ordinal-ignore-case, matching `ContainerHelper`'s comparison style used throughout
`StreamBuilder`).

**`streambuilder.video` / `streambuilder.audio` input** — a serialized `MediaOptions`:

```jsonc
"input": {
  "ItemId": "11d229b72d484b959f9b49f6ab75e613",
  "MediaSourceId": "...",
  "MediaSources": [ /* MediaSourceInfo[] */ ],
  "Profile": { /* DeviceProfile */ },
  "DeviceId": "test-deviceId",
  "MaxBitrate": null,
  "MaxAudioChannels": null,
  "Context": "Streaming",
  "AudioTranscodingBitrate": null,
  "AudioStreamIndex": null,
  "SubtitleStreamIndex": null,
  "EnableDirectPlay": true,
  "EnableDirectStream": false,
  "ForceDirectPlay": false,
  "ForceDirectStream": false,
  "AllowAudioStreamCopy": true,
  "AllowVideoStreamCopy": true,
  "AlwaysBurnInSubtitleWhenTranscoding": false
}
```

Omitted fields take `MediaOptions`' ctor defaults (`MediaOptions.cs:14-20`), which the Go
side must replicate. `EnableDirectStream: false` is shown because
`MediaInfoHelper.cs:248-253` force-clears it unless `ForceDirectStream` is set — a
server-side override the corpus should mirror for realism, not a StreamBuilder behaviour.

`EncoderPreset` (`MediaBrowser.Model/Entities/EncoderPreset.cs`) has 11 members, verified
against the compiled enum: `auto=0, placebo=1, veryslow=2, slower=3, slow=4, medium=5,
fast=6, faster=7, veryfast=8, superfast=9, ultrafast=10`. The protocol accepts the member
name; `VideosController.cs:485` passes `superfast`. This settles open item 4.

**`encodinghelper.progressive` input:**

```jsonc
"input": {
  "kind": "video",                       // "video" -> GetProgressiveVideoFullCommandLine
                                         // "audio" -> GetProgressiveAudioFullCommandLine
  "defaultPreset": "superfast",          // EncoderPreset, video only; VideosController.cs:485
  "outputPath": "/var/lib/jellyfin/transcodes/OUTPUT.mp4",  // audio only (3rd arg)
  "encodingOptions": { /* EncodingOptions, 49 fields */ },
  "state": {
    "transcodingJobType": "Progressive",
    "user": { "enableVideoPlaybackTranscoding": true,
              "enableAudioPlaybackTranscoding": true },  // or null
    /* remaining EncodingJobInfo settable members, PascalCase, as in §1.4 */
    "MediaSource": { /* MediaSourceInfo */ },
    "VideoStream": { /* MediaStream */ },
    "AudioStream": { /* MediaStream */ },
    "SubtitleStream": null,
    "BaseRequest": { "$type": "VideoRequestDto", /* ... */ }
  }
}
```

**`encodinghelper.hls` input** — same shape, with a `StreamState` instead:

```jsonc
"input": {
  "outputPath": "/var/lib/jellyfin/transcodes/OUTPUT.m3u8",
  "isEventPlaylist": false,
  "startNumber": 0,
  "encodingOptions": { /* EncodingOptions */ },
  "state": {
    "transcodingJobType": "Hls",
    "userAgent": "Mozilla/5.0 ... AppleTV",     // StreamState.cs:127 — feeds SegmentLength
    "user": { ... },
    "Request": { "$type": "VideoRequestDto", /* StreamingRequestDto/VideoRequestDto */ },
    /* EncodingJobInfo members */
  }
}
```

`$type` on `BaseRequest`/`Request` is mandatory: `StreamState.IsOutputVideo`
(`StreamState.cs:69`) branches on the runtime type, so `VideoRequestDto` vs
`StreamingRequestDto` changes the argv. `System.Text.Json` will not infer it; the harness
reads `$type` and instantiates explicitly.

### 2.4 Response envelope

```jsonc
// success — streambuilder.*
{ "id": "...", "ok": true, "result": { /* StreamInfo, JsonDefaults write form, or null */ } }

// success — encodinghelper.*
{ "id": "...", "ok": true,
  "result": {
    "raw":  "-analyzeduration 200M ... -y \"/var/lib/jellyfin/transcodes/OUTPUT.mp4\"",
    "argv": ["-analyzeduration", "200M", "...", "-y", "/var/lib/jellyfin/transcodes/OUTPUT.mp4"]
  } }

// thrown exception — a contract outcome, not a harness failure
{ "id": "...", "ok": false,
  "error": { "type": "System.ArgumentException",
             "message": "MediaSourceId is required when a specific audio stream is requested" } }
```

`raw` is the oracle's literal return value. `argv` is the same string put through the
tokenizer of §5.1, emitted by the C# side so that a tokenizer disagreement shows up as a
*diff*, not as a silently-shared bug. The Go side produces both independently. **Both are
compared.**

`error.type` is compared; `error.message` is compared for the `ArgumentException`s thrown by
`ValidateMediaOptions` (whose messages are literals at `StreamBuilder.cs:1676,1681,1688,1693`)
and compared loosely elsewhere — framework-generated messages
(`ArgumentNullException.ThrowIfNull` at `:102`) are .NET-version-dependent and are not a wire
contract.

### 2.5 Ordering and purity

`StreamBuilder` mutates its inputs. `MediaInfoHelper.cs:215-228` sets
`mediaSource.SupportsDirectPlay/DirectStream/Transcoding` *before* the call, and
`:265-276` sets them again *after*; and `StreamInfo.MediaSource` (`StreamInfo.cs:225`) holds
a reference to the very `MediaSourceInfo` that was passed in. **The harness must
deserialize inputs fresh for every request** — never cache a parsed `MediaOptions` across
cases — and must diff `result.MediaSource` as part of the output (§5.2), since post-call
mutation is observable on the wire.

---

## 3. Synthetic capability injection

### 3.1 Why

Per `04-encodinghelper-shape.md`, argv depends on runtime-probed driver facts. If the harness
probes the host, CI results depend on the runner's GPU. Everything in this section exists to
make the diff a pure function of the declared inputs.

`EncodingHelper`'s constructor (`EncodingHelper.cs:161-175`) takes all six of its
dependencies, so injection needs no oracle modification:

```csharp
EncodingHelper(IApplicationPaths, IMediaEncoder, ISubtitleEncoder,
               IConfiguration, IConfigurationManager, IPathManager)
```

(`_appPaths` is stored at `:169` and never read — grep for `_appPaths` in the file returns
only the field declaration `:61` and the assignment `:169`. Bind any mock.)

### 3.2 The `IMediaEncoder` probe surface

`MediaBrowser.Controller/MediaEncoding/IMediaEncoder.cs`. `EncodingHelper` touches 18 distinct
members. Call counts are from a grep over `EncodingHelper.cs`.

| Member | Interface line | Calls | Kind |
|:--|--:|--:|:--|
| `SupportsFilter(string)` | `:110` | 39 | capability set |
| `SupportsHwaccel(string)` | `:103` | 25 | capability set |
| `EncoderVersion` | `:40` | 21 | `Version` |
| `SupportsFilterWithOption(FilterOptionType)` | `:117` | 9 | capability set (9-member enum) |
| `IsVaapiDeviceInteliHD` | `:58` | 8 | bool |
| `SupportsBitStreamFilterWithOption(BitStreamFilterOptionType)` | `:124` | 7 | capability set (5-member enum) |
| `IsVaapiDeviceInteli965` | `:64` | 6 | bool |
| `SupportsEncoder(string)` | `:89` | 4 | capability set |
| `IsVaapiDeviceAmd` | `:52` | 4 | bool |
| `EscapeSubtitleFilterPath(string)` | `:240` | 3 | pure function |
| `SupportsDecoder(string)` | `:96` | 2 | capability set |
| `IsVaapiDeviceSupportVulkanDrmModifier` | `:70` | 2 | bool |
| `IsVaapiDeviceSupportVulkanDrmInterop` | `:76` | 2 | bool |
| `IsVideoToolboxAv1DecodeAvailable` | `:82` | 1 | bool |
| `GetTimeParameter(long)` | `:231` | 1 | pure function |
| `GetInputPathArgument(EncodingJobInfo)` | `:268` | 1 | pure function |
| `GenerateConcatConfig(MediaSourceInfo, string)` | `:283` | 1 | side effect (writes a file) |
| `CanEncodeToAudioCodec(string)` | `ITranscoderSupport.cs:7` | 1 | capability set |

`IsPkeyPauseSupported` (`:46`) is not read by `EncodingHelper`; it gates `-p` pause handling
in `TranscodeManager` and is out of harness scope for argv.

**The string-argument capability sets are closed.** Every call site passes a literal, so the
synthetic profile is an explicit allowlist, not an open predicate:

- `SupportsFilter` — 30 distinct literals:
  `alphasrc`, `bwdif_cuda`, `bwdif_opencl`, `bwdif_videotoolbox`, `deinterlace_vaapi`,
  `flip_vulkan`, `hwupload_cuda`, `hwupload_vaapi`, `libplacebo`, `overlay_cuda`,
  `overlay_rkrga`, `overlay_videotoolbox`, `procamp_vaapi`, `scale_opencl`, `scale_rkrga`,
  `scale_vaapi`, `scale_vt`, `scale_vulkan`, `tonemap_vaapi`, `tonemap_videotoolbox`,
  `tonemapx`, `transpose_cuda`, `transpose_vaapi`, `transpose_vt`, `transpose_vulkan`,
  `vpp_rkrga`, `yadif_cuda`, `yadif_opencl`, `yadif_videotoolbox`.
- `SupportsHwaccel` — 9 literals: `cuda`, `d3d11va`, `drm`, `opencl`, `qsv`, `rkmpp`,
  `vaapi`, `videotoolbox`, `vulkan`.
- `SupportsEncoder` — 2 literals (`aac_at`, `libfdk_aac`) plus one dynamic site: `:235` and
  `:261` pass `preferredEncoder` from `_mjpegCodecMap`. Image-extraction path; include the map
  values in the allowlist for completeness.
- `SupportsDecoder` — no literals; `:670` and `:6538` pass computed decoder names. The
  synthetic profile therefore needs a **decoder allowlist keyed by the names the decoder
  switch can produce** (`GetHardwareVideoDecoder :6428`, `GetHwaccelType :6587`,
  `GetQsvHwVidDecoder :6739`). Enumerating that set exactly is still outstanding — the practical
  approach is to instrument the mock to log every argument it is asked about across a full
  corpus run and freeze the resulting set as the profile. A working
  `SyntheticMediaEncoder` implementing all 18 members from a declarative capability profile
  has been built and exercised end-to-end (see §6 Gate 5a); adding the instrumentation is
  mechanical from there.
- `SupportsFilterWithOption` — full 9-member `FilterOptionType`
  (`MediaBrowser.Controller/MediaEncoding/FilterOptionType.cs:11-51`).
- `SupportsBitStreamFilterWithOption` — full 5-member `BitStreamFilterOptionType`
  (`BitStreamFilterOptionType.cs:11-31`).

The three pure functions are transliterated rather than mocked:
- `EscapeSubtitleFilterPath` — `MediaBrowser.MediaEncoding/Encoder/MediaEncoder.cs:1210-1220`:
  `\`→`/`, then `:`→`\:`, then `'`→`'\\\''`, then `"`→`\"`, in that order. Order matters.
- `GetTimeParameter(long ticks)` and `GetInputPathArgument` — likewise transliterated;
  the harness binds the real implementations' logic via a stub so both sides agree.
- `GenerateConcatConfig` writes a file. In the harness it is a no-op; the argv only
  references the path built at `EncodingHelper.cs:1263`.

### 3.3 Ambient host facts that are **not** injectable — the hard constraint

This is the largest single obstacle to a GPU-free, runner-independent diff, and it is not
mentioned in design doc §4. `EncodingHelper` reads host state directly, bypassing
`IMediaEncoder`:

| Ambient call | Sites in `EncodingHelper.cs` | Effect |
|:--|:--|:--|
| `OperatingSystem.IsWindows()` / `IsLinux()` / `IsMacOS()` | **23** — `:417, 950, 956, 1025-1027, 2121, 4193, 4419-4420, 5027, 5767, 5956, 6589-6591, 6742-6743, 6825, 6898, 6954, 7027, 7092` | selects whole filter-chain pipelines |
| `Environment.OSVersion.Version` (kernel) | `:1076, 2123, 5068, 6471` | i915 hang workarounds; AMD Vulkan fmt modifier (`_minKernelVersionAmdVkFmtModifier = 5.15`, `:72`) |
| `RuntimeInformation.OSArchitecture` | `:6472, 6493` | Arm64 decoder gating |
| `Environment.ProcessorCount` | `:7205` | **`-threads N` in argv** |

Two consequences:

**(a) `-threads` leaks the CI runner's core count into argv.**
`GetNumberOfThreads` (`:7195`) returns
`Math.Min(state?.BaseRequest.CpuCoreLimit ?? encodingOptions.EncodingThreadCount, Environment.ProcessorCount)`
— and returns `0` early if that is `<= 0` (`:7199-7203`). The value lands directly in argv
(`:7672`, `DynamicHlsController.cs:1639`). Mitigation: **every corpus entry sets
`CpuCoreLimit` (or `EncodingOptions.EncodingThreadCount`) to either `0` or `1`**, both of
which are below any plausible `ProcessorCount` and so make the `Math.Min` a no-op. The
corpus schema marks this a required field (§4.1) and the Go side hardcodes the same clamp.
The `Math.Min` remains untested — an accepted, documented hole. Testing it would need a
runner with a pinned core count.

**(b) Windows and macOS pipelines are unreachable on a Linux runner.**
Reading the dispatchers:
- `GetAmdVidFilterChain` (`:4183`) — `isAmfDx11OclSupported = isWindows && ...` (`:4197`);
  on Linux it always falls through to `GetSwVidFilterChain` (`:4205`). So
  `GetAmdDx11VidFiltersPrefered` (`:4211`) is dead on Linux.
- `GetIntelVidFilterChain` (`:4409`) — `isIntelDx11OclSupported = isWindows && ...`
  (`:4426-4429`); `GetIntelQsvDx11VidFiltersPrefered` (`:4455`) is dead on Linux.
- `GetAppleVidFilterChain` (`:5756`) — `isVtFullSupported = isMacOS && ...` (`:5770`);
  `GetAppleVidFiltersPreferred` (`:5785`) is dead on Linux.

Of the **10 argv-producing pipelines** in `04-encodinghelper-shape.md`, only **7** are
reachable from a Linux CI runner: software, `GetNvidiaVidFiltersPrefered`,
`GetIntelQsvVaapiVidFiltersPrefered`, `GetIntelVaapiFullVidFiltersPrefered`,
`GetAmdVaapiFullVidFiltersPrefered`, `GetVaapiLimitedVidFiltersPrefered`,
`GetRkmppVidFiltersPrefered`.

Resolution — pick one, explicitly, and record it:

- **Option A (recommended): pin `host_os = linux`, `host_arch = x86_64`, kernel = a fixed
  version, and declare Windows/macOS argv out of scope.** Justification: the Go port targets
  Kubernetes (design doc §0). The three unreachable pipelines are Windows D3D11 ×2 and macOS
  VideoToolbox ×1 — none of which can run in a Linux container regardless. The Go port should
  then **not implement them at all**, and the corpus must never set
  `HardwareAccelerationType = amf` or `videotoolbox` expecting a hardware chain (both would
  correctly fall back to software). This shrinks §4's coverage matrix from 10 pipelines to 7
  and is the honest scope.
- **Option B: matrix the C# harness across `ubuntu-latest`, `windows-latest`, `macos-latest`
  runners.** Gets all 10, at the cost of the Go side needing a `GOOS`-parameterized argv
  builder that is never exercised in production. Only worth it if a non-Linux target appears.
- **Option C: patch the oracle to route OS checks through an injectable `IPlatformFacts`.**
  Rejected — violates the read-only-oracle decision (design doc §1) and makes every diff
  suspect ("did we diff the oracle, or our edit of it?").

**Decision: Option A.** `host_os`, `host_arch`, and `host_kernel` are declared fields of the
capability profile (§3.5) so that the *assumption is explicit and checkable*, even though the
oracle reads them ambiently. The harness **asserts at startup** that the real host matches the
declared values and aborts if not — so a CI runner change surfaces as a loud failure rather
than a silent behaviour shift.

**Measured on a representative Linux runner** (`dotnet` 10.0.110, container image used by this
project):

| Ambient fact | Value |
|:--|:--|
| `Environment.OSVersion.Version` | `6.18.5.0` |
| `RuntimeInformation.OSArchitecture` | `X64` |
| `OperatingSystem.IsLinux/IsWindows/IsMacOS` | `True/False/False` |
| `Environment.ProcessorCount` | `4` |

Consequences, both confirmed by execution:

- Kernel `6.18.5` is **outside** the i915 hang window (`5.18 ≤ v ≤ 6.1.3`,
  `EncodingHelper.cs:69-71`) and **above** `_minKernelVersionAmdVkFmtModifier` (5.15, `:72`).
  The i915 workaround branches are therefore **permanently uncovered** on this class of
  runner and belong in `known-uncovered.md`. This settles open item 7.
- The `-threads` clamp is **live, not theoretical**: `GetNumberOfThreads` returns
  `0 → 0`, `1 → 1`, `2 → 2`, but `64 → 4` — clamped to `ProcessorCount`. The §3.3(a)
  mitigation (pin every corpus entry to `0` or `1`) is therefore **required**, not
  precautionary.

**Flagged for runtime experiment.** `Environment.OSVersion.Version` on Linux returns the
kernel version. `_minKernelVersionAmdVkFmtModifier = 5.15` (`:72`) and the i915 hang window
`5.18 ≤ v ≤ 6.1.3` with a `6.0.18` carve-out (`:69-71`) mean GitHub-hosted runners
(kernel 6.x) sit *outside* the i915 hang window while many real deployments sit inside it.
The harness therefore cannot exercise the i915 workaround branches at all. Confirming which
branch a given runner takes needs an actual run. This is the clearest case in the whole
document of a behaviour the harness cannot cover.

### 3.4 `ITranscoderSupport` (StreamBuilder side)

Three predicates (`MediaBrowser.Model/Dlna/ITranscoderSupport.cs:7-11`), injected as the
three allowlists in the request envelope (§2.3). In production these are satisfied by
`MediaEncoder` (which implements `IMediaEncoder : ITranscoderSupport`,
`IMediaEncoder.cs:22`). `CanExtractSubtitles` is the one that visibly moves the needle: the
upstream tests parameterize on it directly
(`StreamBuilderTests.cs:665-666`, `:706-707`, `:757-758`).

### 3.5 The injectable capability profiles

Seven profiles, each a JSON document under `fixtures/capabilities/`. Shape:

```jsonc
{
  "name": "intel-ihd",
  "host": { "os": "linux", "arch": "x86_64", "kernel": "6.8.0" },  // asserted, not injected — §3.3
  "encoderVersion": "7.1.1",
  "hwaccels":   ["vaapi", "drm", "opencl", "qsv"],
  "filters":    ["scale_vaapi", "deinterlace_vaapi", "tonemap_vaapi", "procamp_vaapi",
                 "transpose_vaapi", "hwupload_vaapi", "scale_opencl", "alphasrc", "tonemapx"],
  "filterOptions":         ["OverlayVaapiFrameSync", "TonemapOpenclBt2390",
                            "OverlayOpenclFrameSync"],
  "bitStreamFilterOptions":["HevcMetadataRemoveDovi", "HevcMetadataRemoveHdr10Plus",
                            "Av1MetadataRemoveDovi", "Av1MetadataRemoveHdr10Plus",
                            "DoviRpuStrip"],
  "encoders":   ["libfdk_aac"],
  "decoders":   ["h264_qsv", "hevc_qsv", "vp9_qsv", "av1_qsv", "mpeg2_qsv", "vc1_qsv"],
  "vaapiDevice": { "isAmd": false, "isInteliHD": true, "isInteli965": false,
                   "supportsVulkanDrmModifier": false, "supportsVulkanDrmInterop": false },
  "isVideoToolboxAv1DecodeAvailable": false
}
```

| Profile | `encoderVersion` | hwaccels | vaapiDevice | Exercises |
|:--|:--|:--|:--|:--|
| `software` | 7.1.1 | *(none)* | all false | `GetSwVidFilterChain :3853`; every fallback path |
| `intel-ihd` | 7.1.1 | vaapi, drm, opencl, qsv | `isInteliHD` | `GetIntelQsvVaapiVidFiltersPrefered :4747`, `GetIntelVaapiFullVidFiltersPrefered :5078` |
| `intel-i965` | 5.1.2 | vaapi, drm, opencl | `isInteli965` | legacy i965 branches; sits *below* `_minFFmpegOclCuTonemapMode` (5.1.3, `:76`) |
| `amd-vaapi` | 7.1.1 | vaapi, drm, opencl, vulkan | `isAmd`, both Vulkan flags | `GetAmdVaapiFullVidFiltersPrefered :5314` |
| `nvidia` | 7.1.1 | cuda, opencl | all false | `GetNvidiaVidFiltersPrefered :4001` |
| `rkmpp` | 7.1.1 | rkmpp, opencl, drm | all false | `GetRkmppVidFiltersPrefered :5978` |
| `vaapi-limited` | 6.0 | vaapi | all false | `GetVaapiLimitedVidFiltersPrefered :5549` — fails `IsVaapiFullSupported :282` |

Two profiles carry **older `encoderVersion`s on purpose**, to straddle the version gates
enumerated in `04`: `_minFFmpegOclCuTonemapMode = 5.1.3` (`:76`),
`_minFFmpegAdvancedTonemapMode = 7.0.1` (`:82`), `_minFFmpegQsvVppTonemapOption = 7.0.1`
(`:84`), `_minFFmpegAlteredVaVkInterop = 7.0.1` (`:83`), `_minFFmpegVaapiDeviceVendorId = 7.0.1`
(`:86`), `_minFFmpegRkmppHevcDecDoviRpu = 7.1.1` (`:88`), `_minFFmpegImplicitHwaccel = 6.0`
(`:74`), `_minFFmpegHwaUnsafeOutput = 6.0` (`:75`), `_minFFmpegReadrateOption = 5.0` (`:79`),
`_minFFmpegNoiseBsfDrop = 5.0` (`:90`), `_minFFmpegReadrateCatchupOption = 8.0` (`:89`), plus
the three HLS-side gates in `DynamicHlsController.cs:48-50`. **There are 20 ffmpeg version gates across the two files, not the 4 listed in
`04-encodinghelper-shape.md`** — 17 at `EncodingHelper.cs:74-90`, 3 at
`DynamicHlsController.cs:48-50`. (A 21st, `_maxFFmpegCkeyPauseSupported`, lives in
`TranscodeManager.cs:55` and gates process control, not argv.) Seven capability profiles
cannot straddle 20 gates; §4.3 handles this with a version sweep instead.

**Internal-consistency rule the corpus must obey.** `MediaEncoder` only probes the VAAPI
vendor flags when `OperatingSystem.IsLinux() && SupportsHwaccel("vaapi") &&
!string.IsNullOrEmpty(options.VaapiDevice) && options.HardwareAccelerationType ==
HardwareAccelerationType.vaapi` (`MediaBrowser.MediaEncoding/Encoder/MediaEncoder.cs:241-245`).
So on a real Intel iHD machine configured for **QSV**, `IsVaapiDeviceInteliHD` is **false**.
A capability profile paired with `EncodingOptions.HardwareAccelerationType != vaapi` must
therefore set all five `vaapiDevice` flags false, or it describes a machine that cannot exist.
The corpus builder **validates this invariant** and rejects violating triples. Likewise
`isVideoToolboxAv1DecodeAvailable` is only probed on macOS (`MediaEncoder.cs:277-280`) and is
always false under Option A.

---

## 4. Corpus schema

### 4.1 The triple

```jsonc
// fixtures/corpus/<family>/<case>.json
{
  "id": "chrome/mp4-h264-ac3-srt-2600k/intel-ihd/hls",
  "provenance": "captured",              // "captured" | "upstream-fixture" | "synthetic"
  "capturedFrom": {                      // present iff provenance == "captured"
    "clientFamily": "Streamyfin",
    "userAgent": "Streamyfin/0.28.0 CFNetwork/1494.0.7 Darwin/23.4.0",
    "captureFile": "fixtures/capture/streamyfin.ndjson",
    "captureLine": 412
  },
  "deviceProfile":   "fixtures/profiles/DeviceProfile-Chrome.json",
  "mediaSource":     "fixtures/sources/MediaSourceInfo-mp4-h264-ac3-srt-2600k.json",
  "capabilities":    "fixtures/capabilities/intel-ihd.json",
  "transcoderSupport": "fixtures/transcoder/full.json",

  "ops": ["streambuilder.video", "encodinghelper.hls"],

  "mediaSourceOverlay": {                 // §2.2(a): [JsonIgnore]d fields, applied post-deserialize
    "DefaultAudioIndexSource": ["User", "Language"],
    "TranscodeReasons": []
  },

  "mediaOptions": {                       // MediaOptions overlay; ctor defaults elsewhere
    "AudioStreamIndex": null,
    "SubtitleStreamIndex": 2,
    "MaxBitrate": null
  },
  "encodingOptions": "fixtures/encoding/default.json",  // + inline overlay below
  "encodingOptionsOverlay": {
    "HardwareAccelerationType": "qsv",
    "EnableTonemapping": true,
    "EncodingThreadCount": 0               // REQUIRED — see §3.3(a)
  },
  "state": {                               // EncodingJobInfo/StreamState overlay
    "userAgent": "Streamyfin/0.28.0 CFNetwork/1494.0.7 Darwin/23.4.0",
    "user": { "enableVideoPlaybackTranscoding": true,
              "enableAudioPlaybackTranscoding": true },
    "OutputFilePath": "$TRANSCODE_DIR/$SESSION.m3u8"   // placeholder — §5.1
  }
}
```

Files are referenced by path, not inlined, so a `DeviceProfile` shared by 200 cases is stored
once and a corpus-wide profile fix is one edit. The `id` is the protocol `id` (§2.3).

**Required-field rules** (enforced by a corpus linter that runs before the harness):
1. `encodingOptionsOverlay.EncodingThreadCount ∈ {0, 1}` **or**
   `state.BaseRequest.CpuCoreLimit ∈ {0, 1}` — §3.3(a).
2. If `capabilities.vaapiDevice` has any flag true, then
   `encodingOptions.HardwareAccelerationType == "vaapi"` — §3.5.
3. If `encodingOptions.HardwareAccelerationType ∈ {"amf","videotoolbox"}` under
   `host.os == "linux"`, the case is tagged `expects-software-fallback` — a reminder that it
   proves the fallback, not the hardware chain.
4. Every path referenced resolves; every `capabilities.host` matches the harness's asserted
   host.

### 4.2 Seeding from what already exists

The oracle repo already ships most of a `StreamBuilder` corpus. It is not synthetic and it
is not hypothetical — it is checked in:

- **19 `DeviceProfile-*.json`** in `tests/Jellyfin.Model.Tests/Test Data/`:
  AndroidPixel, AndroidTVExoPlayer, AndroidTVExoPlayer-NoHevcRotation, Chrome, Chrome-NoHLS,
  DirectMedia, Firefox, JellyfinMediaPlayer, LowBandwidth, Null, RokuSSPlus, RokuSSPlusNext,
  SafariNext, Tizen3-stereo, Tizen4-4K-5.1, TranscodeMedia, WebOS-23, Yatse, Yatse2.
- **~25 `MediaSourceInfo-*.json`** in the same directory, spanning mp4/mkv containers;
  h264/hevc/vp9/av1 video; aac/ac3/eac3/dts/truehd/vorbis audio; srt/vtt subtitles;
  Dolby Vision profiles 5 and 8 (`dvhe.05`, `dvh1.05`, `dvhe.08`); Hi10P; 32- and 33-stream
  edge cases; a broken-fps case; and a no-streams case.
- **Expected outcomes** already encoded as ~200 `[InlineData]` rows in
  `tests/Jellyfin.Model.Tests/Dlna/StreamBuilderTests.cs:22-...`, each carrying
  `(profile, source, PlayMethod, TranscodeReason mask, transcodeMode, transcodeProtocol)`.

**These become the corpus seed directly.** The `[InlineData]` rows are *not* used as expected
values — the oracle produces truth (design doc §3) — but they are a ready-made enumeration of
interesting `(profile × source)` pairs, and their `TranscodeReason` masks are a useful
sanity check on the harness itself: if the harness's oracle run disagrees with an
`[InlineData]` row, the harness is wired wrong, not the port. **That is the harness's own
first verification gate** (§6, Gate 0) — **discharged: 663/663 pass.**

The 19 profiles do **not** cover the five client families named in design doc §3 (Swiftfin,
findroid, Streamyfin, Android TV, Kodi) — only AndroidTVExoPlayer and Yatse are close. §4.4
closes that gap.

### 4.3 Growing the argv corpus: reachable, not cross-product

`04-encodinghelper-shape.md` is right that the cross product is large and sparse. The corpus
is grown along three axes, each with a bounded generator:

**Axis 1 — pipeline reachability (7 pipelines under Option A).** For each capability profile,
each `HardwareAccelerationType` value it can legally pair with, crossed with
`{sw-decode, hw-decode} × {sw-encode, hw-encode}`. The dispatchers branch on exactly this
(`:4196-4207`, `:4421-4438`, `:5028-5040`, `:5768-5779`, `:5957-5968`), so this axis is
enumerable from the source rather than guessed.

**Axis 2 — cross-cutting concerns.** From `04`: tonemap × deinterlace × subtitle. Driven by
`MediaSourceInfo` content, not by flags:
- tonemap: needs `VideoRange == HDR` and `BitDepth >= 10`; the five predicates
  (`:346, 358, 393, 406, 430`) additionally split on `VideoRangeType ∈ {HDR10, HLG, DOVI}`
  and `IsHdr10Plus` / `IsDoviWithHdr10Bl`. The existing `dvhe.05` / `dvhe.08` / `dvh1.05`
  fixtures already cover three of these; HDR10 and HLG sources must be added.
- deinterlace: `IsDeinterlaceAvailable :448` reads `state.DeInterlace(codec, true)`, i.e.
  the source's `IsInterlaced` plus `EncodingOptions.DeinterlaceMethod`. Two interlaced
  sources (h264, hevc) are needed; none currently exists in the fixture set.
- subtitle: `{none, embed, external-text, external-graphical, burn-in}` — reachable by
  varying `SubtitleDeliveryMethod` and the subtitle stream's `IsExternal` /
  `IsTextSubtitleStream`.

**Axis 3 — ffmpeg version sweep.** 20 version gates (§3.5) cannot be straddled by 7 profiles.
Instead: for a small **anchor set** of cases (one per pipeline × one tonemap-on and one
tonemap-off variant), re-run the case at each of the **distinct gate boundary versions**
— the 7 distinct thresholds `{5.0, 5.1, 5.1.3, 6.0, 7.0.1, 7.1.1, 8.0}` plus a
just-below-lowest `4.4`, i.e. each threshold and its immediate predecessor. That is
8 versions × ~14 anchors = ~112 extra cases, which is cheap because no
process is spawned per case. This covers every gate boundary without a combinatorial blowup.

Coverage is measured, not asserted: the harness's `IMediaEncoder` mock records which
predicates were consulted and which branch each returned, and the driver reports which of the
7 pipelines and which of the 20 gates were exercised by at least one case. **A gate with zero
coverage is a corpus bug and fails the build.**

### 4.4 Growing from captured `DeviceProfile`s

Design doc §3's capture proxy records full request bodies. `DeviceProfile` arrives at
`POST /Items/{itemId}/PlaybackInfo` (`Jellyfin.Api/Controllers/MediaInfoController.cs:116`)
inside `PlaybackInfoDto.DeviceProfile` (read at `:139`). When the body omits it, the server
falls back to the device's stored capabilities (`:141-147`) — so the capture pipeline must
**also** record `POST /Sessions/Capabilities/Full` to catch profiles registered out-of-band.
`GET /Items/{itemId}/PlaybackInfo` (`:72`) carries no profile at all and is not a source.

Extraction (a Go tool in the port repo, `cmd/corpusgen`):
1. Scan `fixtures/capture/*.ndjson` for `PlaybackInfo` POSTs and `Capabilities/Full` POSTs.
2. Extract `$.DeviceProfile`, canonicalize (deep key sort, drop `Id` and `Name`), hash.
3. Dedupe by hash. Write each distinct profile to `fixtures/profiles/<family>-<hash8>.json`
   with the originating `User-Agent` recorded in the corpus entry's `capturedFrom` block.
4. Cross each new profile with **every** `MediaSourceInfo` in `fixtures/sources/` and every
   capability profile, emitting `streambuilder.video` cases (cheap — no argv).
5. For the subset whose oracle `StreamInfo.PlayMethod == Transcode`, emit
   `encodinghelper.*` cases as well, choosing `hls` vs `progressive` from the oracle's
   `SubProtocol`. This is the key economy: **the argv corpus is generated from the
   StreamBuilder corpus's own output**, so it only contains reachable transcode
   configurations.

Step 5 makes the two harnesses a pipeline rather than two independent matrices, and it means
a new client profile automatically grows both.

**Flagged.** Captured `DeviceProfile`s may contain a client-chosen `Id` and user-visible
`Name`. Dropping them in step 2 is safe for `StreamBuilder` — `Id` is read only at
`StreamBuilder.cs:247` / `:67` to populate `StreamInfo.DeviceProfileId`, which the diff
normalizes (§5.2) — but it must be dropped consistently on both sides.

---

## 5. Comparison rules

### 5.1 Argv normalization

**Step 1 — tokenize.** Both sides apply the .NET `ProcessStartInfo.Arguments` parsing rules
(§1.5), because that is the tokenizer the real server's argv is subject to at
`TranscodeManager.cs:431`. Rules: whitespace separates tokens outside quotes; `"` toggles
quoting; `\"` is a literal quote; a run of `n` backslashes before a quote yields `n/2`
backslashes and toggles/escapes accordingly; backslashes not before a quote are literal.
A POSIX tokenizer gets `subtitles=f='/path/with\:colon'` wrong.

The C# side emits its own tokenization alongside `raw` (§2.4) and both are compared, so a
tokenizer bug shows up as a diff rather than cancelling out.

**Step 2 — canonicalize paths.** Absolute paths reach argv from five sources, each of which
gets a stable placeholder applied to both sides before comparison:

| Source | Site | Placeholder |
|:--|:--|:--|
| `state.OutputFilePath` / `outputPath` | `EncodingHelper.cs:7676`, `:7911`; `DynamicHlsController.cs:1650` | `$OUT` |
| HLS segment filename / fmp4 init | `DynamicHlsController.cs:1585-1587, 1600-1604, 1649` | `$OUT-%d`, `$OUT-1` |
| concat config | `EncodingHelper.cs:1263` (`CommonApplicationPaths.CachePath`) | `$CACHE/concat/$MSID.concat` |
| attachment/fonts dir | `EncodingHelper.cs:1928` (`IPathManager.GetAttachmentFolderPath`) | `$FONTS` |
| extracted subtitle file | `EncodingHelper.cs:1965` (`ISubtitleEncoder.GetSubtitleFilePath`) | `$SUB` |
| media input path | `EncodingHelper.cs:1245` → `IMediaEncoder.GetInputPathArgument` | `$MEDIA` |

The mocks are configured to *return* these placeholder strings directly, so the substitution
happens at injection time rather than by post-hoc regex. That is strictly safer: a post-hoc
regex over `subtitles=f='...'` would have to un-do `EscapeSubtitleFilterPath`'s escaping to
find the path. Injecting the placeholder means the escaping is still applied — to the
placeholder — and so remains under test.

**Consequence:** placeholders must be chosen to contain no character that
`EscapeSubtitleFilterPath` (`MediaEncoder.cs:1215-1219`) or `EncodingUtils.NormalizePath`
(`MediaBrowser.MediaEncoding/Encoder/EncodingUtils.cs:78-82`) transforms — no `\`, `:`, `'`,
or `"`. `$OUT`, `$FONTS`, `$SUB`, `$MEDIA`, `$CACHE` all satisfy this. **A second corpus tier
deliberately uses adversarial paths** — containing `:`, `'`, spaces, `"` — with a fixed
literal value on both sides and no placeholder, precisely to test the escaping. Those cases
must be tokenized and compared literally.

**Step 3 — what is *not* normalized.**
- **Token order.** ffmpeg is order-sensitive and the C# builds argv by string concatenation
  in a fixed sequence. Reordering is a real bug.
- **Filtergraph strings.** Compared verbatim, including `,` separators, `[tags]`, and
  `=`/`:` option syntax. The filter chain *is* the deliverable.
- **Numeric formatting.** Every numeric conversion in `EncodingHelper` passes
  `CultureInfo.InvariantCulture` (e.g. `:7667`, `:7702`, `:7899`;
  `DynamicHlsController.cs:1638`). The Go side must match `.` decimal separators and the
  absence of thousands separators, and must reproduce .NET's `double`/`float` round-trip
  shortest-representation formatting. **Flagged for runtime experiment:** .NET's default
  `double.ToString()` (shortest round-trippable since .NET Core 3.0) and Go's
  `strconv.FormatFloat(v, 'g', -1, 64)` agree in the common case but differ in exponent
  formatting (`1E+06` vs `1e+06`). Any argv containing a float — framerate params via
  `GetFramerateParam` (`:1980`), `-force_key_frames expr:gte(t,n_forced*5)` (`:7724`) — needs
  a targeted differential case before the general corpus is trusted.
- **Whitespace inside quoted tokens.** Preserved; that is content.
- **Trailing whitespace outside quotes.** The oracle calls `.Trim()` on the final result
  (`:7677`, `:7914`, `DynamicHlsController.cs:1652`); the tokenizer collapses interior runs.
  No further rule needed.

### 5.2 `StreamInfo` comparison

Compared as a whole object after normalization, not field-by-field allowlist — an allowlist
would silently miss a newly added field.

**Normalized to placeholders before diff** (identity-preserving, value-ignored):

| Field | `StreamInfo.cs` | Rule |
|:--|--:|:--|
| `DeviceProfileId` | `:196` | placeholder; derived from `Profile.Id`, dropped by corpusgen §4.4 |
| `DeviceId` | `:202` | placeholder; echoed from `MediaOptions.DeviceId` |
| `PlaySessionId` | `:249` | placeholder; set by `MediaInfoHelper.cs:262`, not by StreamBuilder |
| `ItemId` | `:39` | placeholder; echoed input |

**Compared exactly — the decision surface.** This is the contract:

`PlayMethod :45`, `SubProtocol :69`, `Container :63`, `VideoCodecs :124`, `AudioCodecs :118`,
`SubtitleCodecs :231`, `SubtitleDeliveryMethod :237`, `SubtitleFormat :243`,
**`TranscodeReasons :255`**, `AudioStreamIndex :130`, `SubtitleStreamIndex :136`,
`AudioBitrate :154`, `AudioSampleRate :160`, `VideoBitrate :166`, `MaxWidth :172`,
`MaxHeight :178`, `MaxFramerate :184`, `TranscodingMaxAudioChannels :142`,
`GlobalMaxAudioChannels :148`, `SegmentLength :81`, `MinSegments :87`, `RequireAvc :92`,
`RequireNonAnamorphic :97`, `CopyTimestamps :102`, `EnableSubtitlesInManifest :112`,
`EstimateContentLength :219`, `TranscodeSeekInfo :214`, `RunTimeTicks :208`,
`StartPositionTicks :75`, `Context :51`, `MediaType :57`, `StreamOptions :261`,
`EnableAudioVbrEncoding :272`, `AlwaysBurnInSubtitleWhenTranscoding :277`.

`TranscodeReasons` is compared as an **exact bitmask**, not a superset/subset. Per `03`, the
reason mask is the single most fragile output — the codec-profile masking at
`StreamBuilder.cs:1367-1377` and the container-suppression filter at `:1409-1412` both produce
*differences in the explanation* with an identical `PlayMethod`. A harness that compared only
`PlayMethod` would pass while shipping a wrong `PlaybackInfo` response. Diff output renders
the mask as a sorted member-name list (matching `JsonFlagEnumConverter`'s write form) so a
failure reads `+SecondaryAudioNotSupported -AudioIsExternal` rather than `0x2040 != 0x1040`.

**`MediaSource` (`:225`) is compared** — specifically `SupportsDirectPlay`,
`SupportsDirectStream`, `SupportsTranscoding`, and `TranscodeReasons` on it — because
StreamBuilder holds and the API layer mutates the same object (§2.5), and those three
booleans are serialized straight into the `PlaybackInfo` response.

**Computed properties are compared too**, at least the ones the API reads: `TargetVideoCodec
:574`, `TargetAudioCodec :545`, `TargetVideoBitrate :635`, `TargetAudioBitrate :506`,
`TargetAudioChannels :521`, `TargetWidth :733`, `TargetHeight :756`, `TargetVideoLevel :403`,
`TargetVideoProfile :442`, `TargetVideoRangeType :466`, `TargetVideoBitDepth :340`,
`TargetFramerate :388`, `TargetRefFrames :364`, `TargetTimestamp :651`, `TargetSize :603`,
`TargetTotalBitrate :669`, `TargetVideoStreamCount :779`, `TargetAudioStreamCount :796`.
They are ~750 lines of independent logic in their own right and are not otherwise exercised
by the settable-field diff.

**`ToUrl` (`:877`) is compared under the design doc §3 URL rule**: the query-param *order*
within the URL is normalized; the param set and values are compared exactly. Driven exactly
as the upstream test does it — `ToUrl("media:", "ACCESSTOKEN", null)`
(`StreamBuilderTests.cs:608`) — so the access token is already a fixed literal and needs no
normalization. This matters because `TranscodingUrl` is a wire field
(`MediaInfoHelper.cs:300`).

**Null result.** `null` from either entry is a legal outcome and compares equal only to
`null`.

---

## 6. Verification gates

No time estimates. Progress is these gates, in order.

**Gate 0 — oracle baseline. DISCHARGED.** `dotnet test tests/Jellyfin.Model.Tests -c Release`
passes **663/663**, including the ~200 `StreamBuilderTests` `[InlineData]` rows that pin
`PlayMethod`, the `TranscodeReason` mask, transcode mode, and protocol. The oracle behaves as
the checked-in expectations claim, so those rows are a valid seed (§4.2) and a valid
self-check for the harness wiring.

*Build note:* `Directory.Build.props:23-24` attaches the in-tree `Jellyfin.CodeAnalysis`
analyzer **only in Debug**. A Debug build fails with `CS9057` when the prebuilt analyzer was
compiled against a newer Roslyn than the installed SDK ships. Building `-c Release` sidesteps
it with no source change, and is what CI should use.

**Gate 1 — protocol round-trip.** Every corpus input deserializes, serializes, and
re-deserializes to an identical object graph on the C# side. Must cover both defects in §2.2:
the `[JsonIgnore]` drop (a) and the `Read` throw (b). **Partly discharged** — the (b) fix is
verified to round-trip byte-identically; the full-corpus sweep remains.

**Gate 2 — host assertion.** The harness aborts on a host whose OS/arch/kernel does not match
the declared capability profile (§3.3). Reference values measured, in §3.3. **[SDK for the
abort path]**

**Gate 3 — StreamBuilder zero-diff.** Every `streambuilder.*` corpus case produces an
identical normalized `StreamInfo` from both implementations. Reported per client family, so
Chrome can be green while WebOS is red (mirrors design doc §3's per-family gate).

**Gate 4 — argv corpus coverage.** The instrumented mock reports ≥1 case exercising each of
the 7 reachable pipelines and each of the 20 ffmpeg version gates. Zero-coverage gates fail
the build. Uncoverable branches (i915 kernel window, `Math.Min` thread clamp, the 3
non-Linux pipelines) are listed in an explicit `known-uncovered.md` with a reason, and the
list is asserted to match — so a branch silently *leaving* coverage is a failure too.

**Gate 5 — EncodingHelper zero-diff.** Every `encodinghelper.*` corpus case produces an
identical token list from both implementations, `raw` and `argv` both.

**Gate 5a — argv without media or GPU. DISCHARGED.** The central premise is confirmed
executable. A `SyntheticMediaEncoder` implementing all 18 `IMediaEncoder` members from a
declarative capability profile, wired into `EncodingHelper` through its constructor
(`:161-175`), produces real argv with no ffmpeg binary, no media file, and no GPU:

```
-i "$MEDIA" -map 0:0 -map 0:1 -map -0:s -codec:v:0 libx264
-force_key_frames "expr:gte(t,n_forced*5)"
-vf "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,format=yuv420p"
-preset veryfast -crf 23
-x264opts:0 subme=0:me_range=16:rc_lookahead=10:me=hex:open_gop=0
-map_metadata -1 -map_chapters -1 -threads 1 -codec:a:0 aac
-f mp4 -movflags frag_keyframe+empty_moov+delay_moov -y "/OUT.mp4"
```

Note the `$MEDIA` placeholder arriving via `IMediaEncoder.GetInputPathArgument` exactly as
§5.1 specifies — injected at the source, not regexed afterwards — and `-threads 1` honouring
the pinned `CpuCoreLimit`.

**Dead parameter discovered here — add it to the transliteration hazard list.** The argv reads
`-preset veryfast` although the call passed `EncoderPreset.superfast`. Tracing it:
`GetVideoQualityParam` (`:2089`) reads `encodingOptions.EncoderPreset` into a local (`:2167`)
and passes it as `GetEncoderParam`'s nullable `preset` parameter (`:1725`), which resolves
`preset ?? defaultPreset` (`:1728`). But `EncodingOptions.EncoderPreset` is a **non-nullable**
enum property that always has a value (`EncodingOptions.cs:221`, defaulted to
`EncoderPreset.auto` at `:46`), so the `??` can never take its right-hand branch.
`defaultPreset` — the third parameter of the public entry point
`GetProgressiveVideoFullCommandLine` — is therefore **unreachable**, and
`VideosController.cs:485`'s `EncoderPreset.superfast` has no effect whatsoever.

Confirmed across the matrix:

| `EncodingOptions.EncoderPreset` | `defaultPreset` | emitted |
|:--|:--|:--|
| `auto` | `superfast` | `-preset veryfast` |
| `auto` | `placebo` | `-preset veryfast` |
| `slow` | `superfast` | `-preset slow` |
| `slow` | `placebo` | `-preset slow` |
| `ultrafast` | `superfast` | `-preset ultrafast` |
| `ultrafast` | `placebo` | `-preset ultrafast` |

Two rules for the port, both of the "transliterate, do not redesign" kind:
`auto` maps to the literal string `veryfast` for libx264/libx265 (`:1731-1735`), and the
`defaultPreset` argument must be **carried but ignored**. A port that "simplifies" by treating
`defaultPreset` as the effective fallback diverges the moment a user sets a non-`auto` preset.
The harness protocol still transmits `defaultPreset` (§2.3) so that the dead parameter stays
under test rather than being quietly dropped.

**Gate 6 — adversarial paths.** The escaping tier of §5.1 (paths with `:`, `'`, `"`, spaces)
is zero-diff.

**Gate 7 — CI wiring.** The whole thing runs on every commit in the Go repo's CI, on a stock
Linux runner, with no GPU, no ffmpeg binary, and no media files. Wall-clock is bounded by the
harness being a single long-lived process.

The workflow is drafted at `docs/design/harness-ci/differential.yml`, staged there rather than
in `.github/workflows/` because it belongs to the **Go** repo — this fork is the read-only
oracle (design §1) and already carries 15 upstream workflow files that ours would collide with.
`docs/design/harness-ci/README.md` records the destination path, the CLI contract each binary
must satisfy, and the gate-to-job mapping.

Two things that workflow settles, both of which correct earlier assumptions:

- **`actions/setup-dotnet`, not the apt route.** The `packages.microsoft.com` procedure in §7
  is a workaround for *this sandbox's* blocked egress; GitHub runners need none of it.
- **A pinned container does not pin the kernel.** Containers share the host kernel, so
  `Environment.OSVersion.Version` still reports the runner's. The host assertion therefore
  transliterates the oracle's own kernel predicates rather than comparing a version string —
  including the `6.0.18 ≤ v < 6.1` carve-out at `EncodingHelper.cs:2124-2126`, which a naive
  `5.18..6.1.3` range check gets wrong and would fail a healthy runner on.

Gates 3 and 5 are the ones design doc §4 names as the primary regression guard. Gates 0–2 and
4 exist because a harness that is wrong in the same direction as the port proves nothing.

---

## 7. Open items

The .NET SDK is **no longer a blocker.** It installs on Ubuntu 24.04 from Microsoft's apt
repository (`packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb`, then
`apt-get install dotnet-sdk-10.0`), which satisfies `global.json`'s `10.0.0 / latestMinor`.
The `dot.net` and `builds.dotnet.microsoft.com` CDNs are blocked by the agent proxy, so the
usual `dotnet-install.sh` route fails; the apt route does not. `api.nuget.org` is reachable,
so restore works. Build with `-c Release` (see Gate 0). Everything below marked RESOLVED was
settled by execution against `dotnet` 10.0.110.

**Resolved by execution.**
1. **RESOLVED — `DynamicHlsController` reflection is viable.** One 11-parameter constructor;
   9 interfaces plus `DynamicHlsHelper` and `EncodingHelper`.
   `GetCommandLineArguments` resolves under `NonPublic | Instance` with the expected
   signature. Full detail in §1.3.
2. **RESOLVED, and the original diagnosis was wrong.** The blocker on `MediaSourceInfo` is
   `[JsonIgnore]` (`:118-122`), not the converter — the fields are silently dropped in both
   directions, which is worse than throwing because it fails green. The `Read` throw is real
   but lands on `StreamInfo.TranscodeReasons`, the output type. The copy-constructor fix
   works for the latter provided the factory is **removed** rather than preceded. Rewritten
   §2.2.
3. **Still open.** The closed set of strings passed to `IMediaEncoder.SupportsDecoder`. The
   `SyntheticMediaEncoder` needed to instrument it now exists and runs (Gate 5a); only the
   logging and a full corpus sweep remain.
4. **RESOLVED.** `EncoderPreset` has 11 members, listed in §2.3 — *and* the `defaultPreset`
   parameter it feeds turns out to be unreachable dead code. See the hazard note under
   Gate 5a.
5. **RESOLVED.** Gate 0 passes 663/663.
7. **RESOLVED.** The runner reports kernel `6.18.5.0`, `X64`, `ProcessorCount = 4` — outside
   the i915 hang window, above the AMD Vulkan modifier threshold. Those branches are
   permanently uncovered on this runner class. The `-threads` clamp is confirmed live
   (`CpuCoreLimit=64 → 4`). Table in §3.3.
9. **RESOLVED — `containerSupported` is fully enumerated, and the suppression is real.**
   Driving `GetOptimalVideoStream` with a `DeviceProfile` whose first `DirectPlayProfile`
   mismatches the container and whose second matches, plus a `CodecProfile` width cap that
   forces `VideoResolutionNotSupported` (outside `DirectStreamReasons`, so every profile
   returns a null `PlayMethod` and evaluation reaches `:1409`):

   | `DirectPlayProfiles` vs `mkv` source | reported `TranscodeReasons` |
   |:--|:--|
   | `[mp4, mkv]` — matched by the second | `VideoResolutionNotSupported` |
   | `[mp4, webm]` — matched by none | `ContainerNotSupported, VideoResolutionNotSupported` |

   Both returned `PlayMethod = Transcode`, proving the early return at `:1404` did not fire.
   So the `.ToArray()` at `:1398` does force full enumeration before the read at `:1411`, and
   a container match anywhere in the list suppresses `ContainerNotSupported` from the
   explanation. **The Go port may use an eager loop**, provided `containerSupported` is
   computed across *all* profiles before the reason is selected. The `03` concern is closed.

**Still needs a runtime experiment.**
6. **Sharpened, not resolved.** .NET's invariant `double.ToString()` was measured across the
   values likely to reach argv. Ordinary framerates and bitrates are safe — `23.976`,
   `29.97`, `59.94`, `0.5`, `123456789.123`, and integral values as `25` / `30` / `1000000`
   (no `.0` suffix) — and Go's `strconv.FormatFloat(v, 'g', -1, 64)` agrees on all of them.
   The divergence is in **exponent form**: .NET emits `1E-07` and `1E+21` where Go emits
   `1e-07` and `1e+21` — different case, and Go drops to exponent form at a different
   magnitude threshold than .NET does. Whether any argv value ever crosses into that range is
   the remaining question; `GetFramerateParam` (`:1980`) and the bitrate params are the
   candidates. Until that is settled the Go side should format argv floats with an explicit
   .NET-compatible routine rather than `%v` or `FormatFloat` defaults.
8. **Unchanged.** Whether real clients send `ProfileCondition`s with `GreaterThanEqual`,
   which would make the dead-code skip at `StreamBuilder.cs:1752-1755` load-bearing. Needs
   captured traffic, not a local run. `corpusgen` (§4.4) should count them.

**Decisions recorded here that the design doc should absorb.**
10. Design doc §4's named entry points are wrong; §0 above supersedes them.
11. Design doc §4 says "10 argv-producing pipelines". Under the Linux-only decision (§3.3,
    Option A) the harness covers **7**, and the Go port should not implement the other 3.
    This narrows Phase 3's scope in design doc §7.
12. `04-encodinghelper-shape.md` lists 4 ffmpeg version gates; there are **20** across
    `EncodingHelper.cs:74-90` (17) and `DynamicHlsController.cs:48-50` (3). §4.3's version sweep exists
    because of this.
