# StreamBuilder — literal transliteration spec

Target: `MediaBrowser.Model/Dlna/StreamBuilder.cs` (2,479 lines), plus
`MediaBrowser.Model/Dlna/ConditionProcessor.cs` (389 lines) and the enum/helper types they
depend on.

`docs/analysis/03-streambuilder-decision-tree.md` is the survey. This document is the
port-this-exactly version: ordered steps, exact predicates, exact bit math, and every place a
clean reimplementation silently diverges.

**The rule is TRANSLITERATE, DO NOT REDESIGN.** Check ordering, reason-bit accumulation, and the
dead code are all required for wire compatibility. Where the C# looks wrong, it is reproduced
here as-is and flagged, not fixed. The contract is the wire — the bytes of `StreamInfo` and the
`TranscodeReasons` bitfield in the `PlaybackInfo` response — not the OpenAPI schema and not what
the code "means".

Unqualified `:NNN` line citations are `MediaBrowser.Model/Dlna/StreamBuilder.cs`. Other files are
named explicitly. Claims that could not be established from source are marked
**[NOT IN SOURCE]**.

---

## 0. Verification gates

No time estimates. The port is done when it clears these gates, in order:

| Gate | What must hold |
|:--|:--|
| G0 | Every enum value in §1 round-trips by numeric value, not by name. |
| G1 | `ConditionProcessor` (§5) matches on every condition in the harness corpus, including the throw cases. |
| G2 | `GetVideoDirectPlayProfile` (§3) returns identical `(Profile, PlayMethod, AudioStreamIndex, TranscodeReasons)` tuples. |
| G3 | `ApplyTranscodingConditions` (§6) produces an identical `StreamOptions` map, including key spelling and the ten unreachable branches never firing. |
| G4 | `BuildVideoItem` (§2) returns byte-identical `StreamInfo`. |
| G5 | The audio path (§4) returns byte-identical `StreamInfo`. |
| G6 | Every quirk in §8 and every hazard in §10 has a corpus case that fails when the quirk is "fixed". |

Gate G6 is the real one. A hazard with no test that fails when you clean it up is not protected.

---

## 1. Data model — exact values

### 1.1 `TranscodeReason` (`MediaBrowser.Model/Session/TranscodeReason.cs:8-47`)

`[Flags]`, 28 bits, non-contiguous by group. Port as a `uint32` with these exact shifts. The
wire serializes this as a comma-joined list of member names, so the *names* matter as much as
the bits.

| Bit | Value | Member | Source line |
|--:|--:|:--|--:|
| 0 | 0x00000001 | `ContainerNotSupported` | :11 |
| 1 | 0x00000002 | `VideoCodecNotSupported` | :12 |
| 2 | 0x00000004 | `AudioCodecNotSupported` | :13 |
| 3 | 0x00000008 | `SubtitleCodecNotSupported` | :14 |
| 4 | 0x00000010 | `AudioIsExternal` | :15 |
| 5 | 0x00000020 | `SecondaryAudioNotSupported` | :16 |
| 6 | 0x00000040 | `VideoProfileNotSupported` | :20 |
| 7 | 0x00000080 | `VideoLevelNotSupported` | :23 |
| 8 | 0x00000100 | `VideoResolutionNotSupported` | :24 |
| 9 | 0x00000200 | `VideoBitDepthNotSupported` | :25 |
| 10 | 0x00000400 | `VideoFramerateNotSupported` | :26 |
| 11 | 0x00000800 | `RefFramesNotSupported` | :28 |
| 12 | 0x00001000 | `AnamorphicVideoNotSupported` | :29 |
| 13 | 0x00002000 | `InterlacedVideoNotSupported` | :30 |
| 14 | 0x00004000 | `AudioChannelsNotSupported` | :33 |
| 15 | 0x00008000 | `AudioProfileNotSupported` | :34 |
| 16 | 0x00010000 | `AudioSampleRateNotSupported` | :35 |
| 17 | 0x00020000 | `AudioBitDepthNotSupported` | :36 |
| 18 | 0x00040000 | `ContainerBitrateExceedsLimit` | :39 |
| 19 | 0x00080000 | `VideoBitrateNotSupported` | :40 |
| 20 | 0x00100000 | `AudioBitrateNotSupported` | :41 |
| 21 | 0x00200000 | `UnknownVideoStreamInfo` | :44 |
| 22 | 0x00400000 | `UnknownAudioStreamInfo` | :45 |
| 23 | 0x00800000 | `DirectPlayError` | :46 |
| 24 | 0x01000000 | `VideoRangeTypeNotSupported` | :21 |
| 25 | 0x02000000 | `VideoCodecTagNotSupported` | :22 |
| 26 | 0x04000000 | `StreamCountExceedsLimit` | :17 |
| 27 | 0x08000000 | `VideoRotationNotSupported` | :27 |

`UnknownVideoStreamInfo` (bit 21) and `UnknownAudioStreamInfo` (bit 22) are never set anywhere in
`StreamBuilder.cs`. Define them; never produce them.

### 1.2 Group aliases (`:22-27`)

Compile-time constants. Reproduce as constants, not as computed sets.

```
ContainerReasons    = ContainerNotSupported | ContainerBitrateExceedsLimit         // :22 = 0x00040001
AudioCodecReasons   = AudioBitrateNotSupported | AudioChannelsNotSupported         // :23
                    | AudioProfileNotSupported | AudioSampleRateNotSupported
                    | SecondaryAudioNotSupported | AudioBitDepthNotSupported
                    | AudioIsExternal                                              //      = 0x0011C030
AudioReasons        = AudioCodecNotSupported | AudioCodecReasons                   // :24 = 0x0011C034
VideoCodecReasons   = VideoResolutionNotSupported | AnamorphicVideoNotSupported    // :25
                    | InterlacedVideoNotSupported | VideoBitDepthNotSupported
                    | VideoBitrateNotSupported | VideoFramerateNotSupported
                    | VideoLevelNotSupported | RefFramesNotSupported
                    | VideoRangeTypeNotSupported | VideoProfileNotSupported
                    | VideoRotationNotSupported                                    //      = 0x090837C0
VideoReasons        = VideoCodecNotSupported | VideoCodecReasons                   // :26 = 0x090837C2
DirectStreamReasons = AudioReasons | ContainerNotSupported                         // :27
                    | VideoCodecTagNotSupported                                    //      = 0x0211C035
```

Note what `VideoCodecReasons` does **not** contain: `VideoCodecTagNotSupported` (bit 25). It is in
`DirectStreamReasons` instead. That asymmetry is the reason a codec-tag mismatch is remuxable
while a video-profile mismatch is not.

`ContainerReasons` includes `ContainerBitrateExceedsLimit`, but inside
`GetVideoDirectPlayProfile` that bit can never be set (§3.9), so in the ranking it behaves as
`ContainerNotSupported` alone.

### 1.3 `ProfileConditionType` (`MediaBrowser.Model/Dlna/ProfileConditionType.cs:5-12`)

Five operators. Serialized by name on the wire, compared by value internally.

| Value | Member |
|--:|:--|
| 0 | `Equals` |
| 1 | `NotEquals` |
| 2 | `LessThanEqual` |
| 3 | `GreaterThanEqual` |
| 4 | `EqualsAny` |

### 1.4 `ProfileConditionValue` (`MediaBrowser.Model/Dlna/ProfileConditionValue.cs:5-33`)

26 members. **The enum skips 15.** Do not port as a contiguous range or as an ordinal index.

| Value | Member | | Value | Member |
|--:|:--|--|--:|:--|
| 0 | `AudioChannels` | | 14 | `RefFrames` |
| 1 | `AudioBitrate` | | *15* | *(unused)* |
| 2 | `AudioProfile` | | 16 | `NumAudioStreams` |
| 3 | `Width` | | 17 | `NumVideoStreams` |
| 4 | `Height` | | 18 | `IsSecondaryAudio` |
| 5 | `Has64BitOffsets` | | 19 | `VideoCodecTag` |
| 6 | `PacketLength` | | 20 | `IsAvc` |
| 7 | `VideoBitDepth` | | 21 | `IsInterlaced` |
| 8 | `VideoBitrate` | | 22 | `AudioSampleRate` |
| 9 | `VideoFramerate` | | 23 | `AudioBitDepth` |
| 10 | `VideoLevel` | | 24 | `VideoRangeType` |
| 11 | `VideoProfile` | | 25 | `NumStreams` |
| 12 | `VideoTimestamp` | | 26 | `VideoRotation` |
| 13 | `IsAnamorphic` | | | |

### 1.5 Other enums

| Enum | File | Values |
|:--|:--|:--|
| `PlayMethod` | `MediaBrowser.Model/Session/PlayMethod.cs:6-22` | `Transcode`=0, `DirectStream`=1, `DirectPlay`=2 |
| `MediaStreamProtocol` | `Jellyfin.Data.Enums` | `http`=0, `hls`=1 (lowercase on the wire) |
| `DlnaProfileType` | `MediaBrowser.Model/Dlna/DlnaProfileType.cs:5-12` | `Audio`=0, `Video`=1, `Photo`=2, `Subtitle`=3, `Lyric`=4 |
| `CodecType` | `MediaBrowser.Model/Dlna/CodecType.cs:6-22` | `Video`=0, `VideoAudio`=1, `Audio`=2 |
| `SubtitleDeliveryMethod` | `MediaBrowser.Model/Dlna/SubtitleDeliveryMethod.cs:8-34` | `Encode`=0, `Embed`=1, `External`=2, `Hls`=3, `Drop`=4 |
| `AudioIndexSource` | `MediaBrowser.Model/MediaInfo/AudioIndexSource.cs:9-30` | `[Flags]` `None`=0, `Default`=1, `Language`=2, `User`=4 |

`PlayMethod` ordering matters: `GetVideoDirectPlayProfile` sorts by it *descending*, so
`DirectPlay` (2) > `DirectStream` (1) > `Transcode` (0) > `null`.

### 1.6 `ProfileCondition` default (`MediaBrowser.Model/Dlna/ProfileCondition.cs:10-26`)

The parameterless constructor sets `IsRequired = true` (:12). The three-argument constructor
sets `IsRequired = false` (:16-17). Deserialized-from-client conditions therefore default to
**required** when the attribute is absent. `IsRequired` is only consulted when the *actual* value
is unknown (§5.2).

### 1.7 `ContainerHelper.ContainsContainer` (`MediaBrowser.Model/Extensions/ContainerHelper.cs`)

Every container and codec match in the whole file bottoms out here. Three behaviours to
transliterate:

1. `ContainsContainer(profileContainers, inputContainer)` (:21-31, :42-52) — if
   `profileContainers` starts with `-`, strip it and set `isNegativeList = true`, then delegate.
2. Empty/null `inputContainer` → return `isNegativeList` (:65-68). Note this is checked
   **before** the empty-profile check in the string overload.
3. Empty/null `profileContainers` → return `true` unconditionally (:84-88). **"Empty profile
   supports everything."** This is why a `DirectPlayProfile` with no `VideoCodec` matches every
   video codec.
4. Otherwise: split both sides on `,`, skip empty segments, ordinal-case-insensitive compare;
   any match → `!isNegativeList`; no match → `isNegativeList` (:90-106).

`ContainerHelper.Split(input)` (:145-148) is `input?.Split(',', RemoveEmptyEntries) ?? []`.

`DirectPlayProfile.SupportsVideoCodec` additionally requires `Type == Video`
(`DirectPlayProfile.cs:50-53`); `SupportsAudioCodec` requires `Type == Audio || Type == Video`
(`:60-64`).

`CodecProfile.ContainsAnyCodec` (`CodecProfile.cs:64-93`): if `useSubContainer` is true **and**
`Container` equals `"hls"` case-insensitively, match against `SubContainer` instead of
`Container`. The codec side is matched with `isNegativeList = false` explicitly, so a leading `-`
in `Codec` is *not* treated as negation.

---

## 2. Video path — control flow

### 2.1 `GetOptimalVideoStream` (`:230`)

1. `ValidateMediaOptions(options, isMediaSource: true)` (`:232` → `:1667`).
   - `options.ItemId` empty → `options.DeviceId` must be non-empty (`:1669-1672`).
   - `options.Profile` null → throw `"Profile is required"` (`:1674-1677`).
   - `options.MediaSources` null → throw `"MediaSources is required"` (`:1679-1682`).
   - `AudioStreamIndex` set with empty `MediaSourceId` → throw (`:1686-1689`).
   - `SubtitleStreamIndex` set with empty `MediaSourceId` → throw (`:1691-1694`).
2. Filter media sources: all of them when `MediaSourceId` is empty, otherwise those whose `Id`
   matches ordinal-case-insensitively (`:234-236`).
3. For each surviving source, `BuildVideoItem(mediaSourceInfo, options)` (`:241`); append
   non-null results (`:242-245`). Source order is preserved.
4. **After** the loop, stamp `DeviceId` and `DeviceProfileId` on every stream (`:248-252`).
   `DeviceProfileId` is `Profile.Id?.ToString("N", InvariantCulture)` — 32 lowercase hex digits,
   no dashes, or null.
5. `GetOptimalStream(streams, options.GetMaxBitrate(false) ?? 0)` (`:254`).

### 2.2 `GetOptimalStream` / `SortMediaSources` (`:257`, `:260`)

`GetOptimalStream` is `SortMediaSources(...).FirstOrDefault()` (`:258`) — null when the list is
empty.

`SortMediaSources` is a five-key ordering (`:262-302`). LINQ `OrderBy`/`ThenBy` is a **stable**
sort; the final key makes it total anyway.

| # | Key | Expression | Line |
|--:|:--|:--|--:|
| 1 | asc | `0` if `PlayMethod == DirectPlay && MediaSource?.Protocol == File`, else `1` | :262-270 |
| 2 | asc | `0` if `PlayMethod` is `DirectStream` or `DirectPlay`, else `1` | :271-281 |
| 3 | asc | `0` if `MediaSource?.Protocol == File`, else `1` | :282-290 |
| 4 | asc | `abs(MediaSource.Bitrate - maxBitrate)` when `maxBitrate > 0` and `Bitrate` is non-null, else `0` | :291-301 |
| 5 | asc | `streams.IndexOf(i)` — original build order | :302 |

Key 4 returns `long`; keys 1-3 and 5 return `int`. Key 5 uses `List.IndexOf`, i.e. reference
identity for `StreamInfo`. Port as "index within the input slice".

`options.GetMaxBitrate(isAudio)` (`MediaBrowser.Model/Dlna/MediaOptions.cs:120-143`):
`MaxBitrate` if set; else null if no profile; else when `Context == Static`,
`Profile.MaxStaticMusicBitrate` if `isAudio` and set, otherwise `Profile.MaxStaticBitrate`;
else `Profile.MaxStreamingBitrate`.

### 2.3 `BuildVideoItem` (`:646`) — ordered steps

Never returns null (declared `StreamInfo`, not `StreamInfo?`). Throws if `item` is null (`:648`).

**Step 1 — construct `playlistItem`** (`:650-660`) with `ItemId`, `MediaType = Video`,
`MediaSource = item`, `RunTimeTicks`, `Context`, `DeviceProfile`,
`AlwaysBurnInSubtitleWhenTranscoding`, and
`SubtitleStreamIndex = options.SubtitleStreamIndex ?? GetDefaultSubtitleStreamIndex(item, options.Profile.SubtitleProfiles)`.

`GetDefaultSubtitleStreamIndex` (`:549-590`): find the highest `Score` among subtitle streams
(`:551-560`, initial `highestScore = -1`, streams with null `Score` ignored); collect all
subtitle streams at that score (`:562-569`); if more than one, return the index of the first
stream (outer loop) for which some profile (inner loop) has `Method == External` **and**
(`IsVobSubMksProfile(profile, stream)` or (`!IsVobSubMksDeliveryProfile(profile)` and
`profile.Format` equals `stream.Codec` ordinal-ignore-case)) (`:572-586`). Otherwise
`item.DefaultSubtitleStreamIndex` (`:589`). The stream loop is outer, the profile loop inner —
stream order wins over profile order.

**Step 2 — resolve the subtitle stream** (`:662`):
`SubtitleStreamIndex.HasValue ? item.GetMediaStream(Subtitle, idx) : null`. Can be null even when
the index is set.

**Step 3 — resolve the audio stream** (`:664-668`):
`item.GetDefaultAudioStream(options.AudioStreamIndex ?? item.DefaultAudioStreamIndex)`.
`GetDefaultAudioStream` (`MediaBrowser.Model/Dto/MediaSourceInfo.cs:175-207`): if the requested
index is non-null and `!= -1`, return the audio stream at that index; else the first audio stream
with `IsDefault`; else the first audio stream; else null. If non-null, set
`playlistItem.AudioStreamIndex`.

**Step 4 — build `candidateAudioStreams`** (`:670-706`). Start as `[]` if `audioStream` is null,
else `[audioStream]` (`:671`). Then, **only if** `!item.DefaultAudioIndexSource.HasFlag(User)`
**and** `options.AudioStreamIndex is null or < 0` (`:673`):

- If `DefaultAudioIndexSource == None` exactly **and** `audioStream is not null` (`:676`):
  all audio streams (`:678`); then, if `audioStream.IsDefault`, narrow to those with `IsDefault`
  (`:679-683`).
- If `HasFlag(Language)` (`:686`): **replace** (not intersect) with all audio streams whose
  `Language == audioStream?.Language` (`:689`). Then if also `HasFlag(Default)` (`:690`), take
  the default streams among those; if that is empty, fall back to *all* default audio streams
  regardless of language (`:692-698`).
- `else if HasFlag(Default)` (`:701`): all audio streams with `IsDefault` (`:704`).

The `Language` branch and the `else if Default` branch are mutually exclusive with each other.
The `None` branch is written as a **separate, preceding `if`**, so structurally it could run and
then be overwritten by the `Language` branch — it cannot in practice, since `None == 0` carries no
flags. Transliterate the three-block structure as written rather than collapsing it into a
switch.

**Step 5 — eligibility** (`:708-724`):

```
videoStream               = item.VideoStream
bitrateLimitExceeded      = IsBitrateLimitExceeded(item, options.GetMaxBitrate(false) ?? 0)   // :710
isEligibleForDirectPlay   = options.EnableDirectPlay   && (options.ForceDirectPlay   || !bitrateLimitExceeded)  // :711
isEligibleForDirectStream = options.EnableDirectStream && (options.ForceDirectStream || !bitrateLimitExceeded)  // :712
transcodeReasons          = 0                                                                  // :713

if item.VideoType == Dvd || item.VideoType == BluRay:  isEligibleForDirectPlay = false          // :716-719
if bitrateLimitExceeded:  transcodeReasons = ContainerBitrateExceedsLimit                       // :721-724
```

The DVD/BluRay clause clears **only** direct play. Direct stream survives. And it runs *after*
`ForceDirectPlay` has already been folded in, so `ForceDirectPlay` does **not** rescue a
BD/DVD folder here — but `GetVideoDirectPlayProfile` short-circuits on `ForceDirectPlay` before
looking at eligibility at all (§3.1), and that short-circuit is reached because `:734` also tests
`isEligibleForDirectStream`. See hazard H7.

`IsBitrateLimitExceeded` (`:1641-1665`): `false` if `item.IsRemote` (`:1644-1647`);
`requestedMaxBitrate = maxBitrate > 0 ? maxBitrate : int.MaxValue` (`:1650`);
`itemBitrate = item.Bitrate ?? 40_000_000` (`:1653`); return `itemBitrate > requestedMaxBitrate`.
The 40 Mbps default for unknown bitrate is a deliberate force-transcode.

`transcodeReasons` is assigned `=`, not `|=`, at `:723`.

**Step 6 — direct play / direct stream attempt** (`:733-790`). Only entered when
`isEligibleForDirectPlay || isEligibleForDirectStream` (`:734`).

```
directPlayInfo   = GetVideoDirectPlayProfile(options, item, videoStream, audioStream,
                                             candidateAudioStreams, subtitleStream,
                                             isEligibleForDirectPlay, isEligibleForDirectStream)  // :737
directPlay       = directPlayInfo.PlayMethod                                                      // :738
transcodeReasons |= directPlayInfo.TranscodeReasons                                                // :739
```

If `directPlay.HasValue` (`:741`):

- `directPlayProfile = directPlayInfo.Profile` (`:743`)
- `playlistItem.PlayMethod = directPlay.Value` (`:744`)
- `playlistItem.Container = NormalizeMediaSourceFormatIntoSingleContainer(item.Container, options.Profile, Video, directPlayProfile)` (`:745`)
- `playlistItem.VideoCodecs = videoStream?.Codec is null ? [] : [codec]` (`:746-747`)

Then, if `directPlay == DirectPlay` (`:749-760`):
- `SubProtocol = http` (`:751`)
- `audioStreamIndex = directPlayInfo.AudioStreamIndex ?? audioStream?.Index` (`:753`)
- if set: `AudioStreamIndex = audioStreamIndex`, and `AudioCodecs` = the codec of
  `item.GetMediaStream(Audio, audioStreamIndex)` or `[]` if that stream/codec is null (`:754-759`)

Else if `directPlay == DirectStream` (`:761-771`):
- `AudioStreamIndex = audioStream?.Index` (`:763`)
- if `audioStream is not null`: `AudioCodecs = Split(directPlayProfile?.AudioCodec)` (`:764-767`)
- `SetStreamInfoOptionsFromDirectPlayProfile(...)` (`:769` → `:631`)
- `BuildStreamVideoItem(playlistItem, options, item, videoStream, audioStream, candidateAudioStreams, directPlayProfile?.Container, directPlayProfile?.VideoCodec, directPlayProfile?.AudioCodec)` (`:770`)

Then, if `subtitleStream is not null` (`:773-779`): `GetSubtitleProfile(item, subtitleStream,
options.Profile.SubtitleProfiles, directPlay.Value, _transcoderSupport,
directPlayProfile?.Container, transcodingSubProtocol: null)` and copy `Method` → 
`SubtitleDeliveryMethod`, `Format` → `SubtitleFormat`. **`SubtitleCodecs` is not set on this
path** (contrast `:813`).

`SetStreamInfoOptionsFromDirectPlayProfile` (`:631-644`) — note it mutates the **input**
`MediaSourceInfo`:
```
container = NormalizeMediaSourceFormatIntoSingleContainer(item.Container, options.Profile, Video, directPlayProfile)  // :633
item.TranscodingContainer   = container            // :636   <-- mutates the media source
item.TranscodingSubProtocol = http                 // :637   <-- mutates the media source
playlistItem.Container      = container            // :639
playlistItem.SubProtocol    = http                 // :640
playlistItem.VideoCodecs    = [item.VideoStream.Codec]      // :642  — unguarded null deref if VideoStream is null
playlistItem.AudioCodecs    = Split(directPlayProfile?.AudioCodec)  // :643
```

**Step 7 — `playlistItem.TranscodeReasons = transcodeReasons`** (`:792`). Plain **assignment**.
Anything `BuildStreamVideoItem` OR-ed into `playlistItem.TranscodeReasons` at `:770` is destroyed
here. See hazard H1.

**Step 8 — transcode** (`:794-821`). Entered when `PlayMethod` is neither `DirectStream` nor
`DirectPlay` (`:794`). Note `StreamInfo.PlayMethod` defaults to `Transcode` (0), so this is also
the path taken when step 6 was skipped entirely.

```
(transcodingProfile, playMethod) = GetVideoTranscodeProfile(item, options, videoStream, audioStream, playlistItem)  // :798
if transcodingProfile is not null && playMethod.HasValue:                                        // :800
    SetStreamInfoOptionsFromTranscodingProfile(item, playlistItem, transcodingProfile)           // :802
    BuildStreamVideoItem(playlistItem, options, item, videoStream, audioStream,
                         candidateAudioStreams, transcodingProfile.Container,
                         transcodingProfile.VideoCodec, transcodingProfile.AudioCodec)           // :804
    playlistItem.PlayMethod = PlayMethod.Transcode                                               // :806
    if subtitleStream is not null:                                                               // :808
        sp = GetSubtitleProfile(item, subtitleStream, Profile.SubtitleProfiles, Transcode,
                                _transcoderSupport, transcodingProfile.Container,
                                transcodingProfile.Protocol)                                     // :810
        playlistItem.SubtitleDeliveryMethod = sp.Method                                          // :811
        playlistItem.SubtitleFormat         = sp.Format                                          // :812
        playlistItem.SubtitleCodecs         = [sp.Format]                                        // :813
    if (playlistItem.TranscodeReasons & (VideoReasons | ContainerBitrateExceedsLimit)) != 0:     // :816
        ApplyTranscodingConditions(playlistItem, transcodingProfile.Conditions, null, true, true) // :818
```

`:806` overwrites `PlayMethod` with `Transcode` **unconditionally**, discarding the
`DirectStream` that `GetVideoTranscodeProfile` may have returned. See hazard H2.

The `:816` guard means the transcoding profile's own conditions are applied only when the
accumulated reasons intersect `VideoReasons | ContainerBitrateExceedsLimit` — a pure
audio-codec failure does **not** trigger them.

**Step 9 — epilogue** (`:823-834`). A debug log that calls `playlistItem.ToUrl("media:", "<token>", null)`
(`:831`) — pure formatting, no state change, but it is on the hot path; if the port's `ToUrl`
panics on a half-built item, the C# does not. Then:

```
item.Container = NormalizeMediaSourceFormatIntoSingleContainer(item.Container, options.Profile, Video, directPlayProfile)  // :833
return playlistItem                                                                                                        // :834
```

`:833` mutates the caller's `MediaSourceInfo.Container`. Because `GetOptimalVideoStream` iterates
sources in a loop with one `MediaSourceInfo` each, this does not leak across items — but the
`MediaSourceInfo` is the same object the caller serializes into the `PlaybackInfo` response, so
the mutation **is** observable on the wire.

`NormalizeMediaSourceFormatIntoSingleContainer` (`:406-433`): returns `inputContainer` unchanged
when `profile is null`, `inputContainer` is empty, or it contains no comma (`:409-412`).
Otherwise split on `,`; candidate profiles are `[playProfile]` when `playProfile` is non-null,
else `profile.DirectPlayProfiles` (`:415`); return the first format (outer loop) for which some
candidate profile (inner loop) has `Type == type` and `SupportsContainer(format)` (`:417-430`);
fall back to the unmodified `inputContainer` (`:432`). Format order is outer, profile order inner.

### 2.4 `GetVideoTranscodeProfile` (`:837`)

1. `mediaSource = playlistItem.MediaSource`; throw if null (`:844-846`).
2. If `!(item.SupportsTranscoding || item.SupportsDirectStream)` → `(null, null)` (`:848-851`).
3. Candidates: `options.Profile.TranscodingProfiles` where `Type == playlistItem.MediaType` and
   `Context == options.Context` (`:853-854`).
4. If `item.UseMostCompatibleTranscodingProfile`, narrow to `Container == "ts"`
   (case-insensitive) (`:856-859`).
5. For each candidate, in client-supplied order, compute a rank pair
   `(Video, Audio)` both initialised to `3` (`:867`):
   - **Video** (`:871-877`): if `videoStream is not null` **and** `options.AllowVideoStreamCopy`
     **and** `ContainerHelper.ContainsContainer(transcodingProfile.VideoCodec, videoCodec)`, then
     `rank.Video = GetCompatibilityVideoCodec(options, mediaSource, container, videoStream) == 0 ? 1 : 2`.
     Otherwise it stays `3`.
   - **Audio** (`:879-906`): if `audioStream is not null` and `options.AllowAudioStreamCopy`,
     iterate `Split(transcodingProfile.AudioCodec)` **in order**; for each,
     `failures = GetCompatibilityAudioCodec(options, mediaSource, container, audioStream, transcodingAudioCodec, isVideo: true, isSecondaryAudio: false)`;
     `rankAudio = 3`, but if `failures == 0` then `rankAudio = (transcodingAudioCodec == audioCodec, ordinal-ignore-case) ? 1 : 2`;
     `rank.Audio = min(rank.Audio, rankAudio)`; break as soon as `rank.Audio == 1`.
   - `playMethod = rank.Video == 1 ? DirectStream : Transcode` (`:908-913`).
6. `OrderBy(analysis => analysis.Rank)` (`:917`). `Rank` is a `ValueTuple<int,int>`; C# compares
   it **lexicographically — `Video` first, then `Audio`**. `OrderBy` is stable, so ties keep
   client-supplied profile order.
7. `analyzedProfiles.FirstOrDefault()` (`:919`). On an empty sequence this returns the
   **default value tuple**: `Profile = null`, `PlayMethod = Transcode` (0), `Rank = (0,0)` — not
   null. The caller's `playMethod.HasValue` test at `:800` is therefore always true; only the
   `transcodingProfile is not null` half of that condition does any work.

`SetStreamInfoOptionsFromTranscodingProfile` (`:592-629`) — again mutates the input
`MediaSourceInfo` at `:597-598`:
```
item.TranscodingContainer   = transcodingProfile.Container    // :597
item.TranscodingSubProtocol = transcodingProfile.Protocol     // :598
if playlistItem.PlayMethod == Transcode:                      // :600   (still the default here)
    playlistItem.Container   = transcodingProfile.Container   // :602
    playlistItem.SubProtocol = transcodingProfile.Protocol    // :603
playlistItem.TranscodeSeekInfo        = transcodingProfile.TranscodeSeekInfo         // :606
if int.TryParse(transcodingProfile.MaxAudioChannels, Invariant, out n):
    playlistItem.TranscodingMaxAudioChannels = n                                     // :607-610
playlistItem.EstimateContentLength    = transcodingProfile.EstimateContentLength     // :612
playlistItem.CopyTimestamps           = transcodingProfile.CopyTimestamps            // :614
playlistItem.EnableSubtitlesInManifest= transcodingProfile.EnableSubtitlesInManifest // :615
playlistItem.EnableMpegtsM2TsMode     = transcodingProfile.EnableMpegtsM2TsMode      // :616
playlistItem.EnableAudioVbrEncoding   = transcodingProfile.EnableAudioVbrEncoding    // :618
if transcodingProfile.MinSegments  > 0: playlistItem.MinSegments  = ...              // :620-623
if transcodingProfile.SegmentLength> 0: playlistItem.SegmentLength= ...              // :625-628
```

The `:600` guard is why the *audio* path (§4.5) sets container/protocol here but the video
direct-stream path at `:769-770` does not — on that path `PlayMethod` is already `DirectStream`.

### 2.5 `BuildStreamVideoItem` (`:924`) — ordered steps

Called twice: for direct stream (`:770`) and for transcode (`:804`). Argument `container` is the
*output* container (direct-play-profile container or transcoding-profile container).

**V1 — video codec list** (`:936-954`):
```
videoCodecs = Split(videoCodec)                                        // :936
if videoCodecs is empty && videoStream is not null: append videoStream.Codec   // :938-942
if playlistItem.SubProtocol == hls: keep only codecs in
      ["h264","hevc","vp9","av1"]                                      // :945-948, allowlist at :31
playlistItem.VideoCodecs = videoCodecs                                 // :950
if videoStream is not null && !ContainsContainer(videoCodecs, false, videoStream.Codec):
      playlistItem.TranscodeReasons |= VideoCodecNotSupported          // :951-954
```
The HLS filter is a hardcoded allowlist, not profile-driven. The `ContainsContainer` overload
used at `:951` is the `IReadOnlyList<string>` one (`ContainerHelper.cs:118-139`), which returns
`true` when the list is **null** — but never here, since `Split` returns `[]`, and an empty list
falls through the loops and returns `isNegativeList == false`.

**V2 — copy source video options** (`:957-972`). `qualifier = videoStream?.Codec` (`:958`).
```
playlistItem.MaxFramerate = videoStream?.ReferenceFrameRate            // :957  (unconditional overwrite)
if videoStream?.Level    is not null: SetOption(qualifier, "level",         Level.ToString(Invariant))   // :959-962
if videoStream?.BitDepth is not null: SetOption(qualifier, "videobitdepth", BitDepth.ToString(Invariant))// :964-967
if videoStream?.Profile  non-empty:   SetOption(qualifier, "profile",       Profile.ToLowerInvariant())  // :969-972
```

**V3 — audio codec list** (`:975-994`):
```
audioCodecs = Split(audioCodec)                                        // :975
if audioCodecs is empty && audioStream is not null: append audioStream.Codec   // :977-981
if playlistItem.SubProtocol == hls:                                    // :984
    if playlistItem.Container == "mp4" (ordinal-ignore-case): keep only codecs in
        ["aac","ac3","eac3","mp3","alac","flac","opus","dts","truehd"]  // :986-989, allowlist at :33
    else: keep only codecs in ["aac","ac3","eac3","mp3"]                // :990-993, allowlist at :32
```
The MP4-vs-TS test uses `playlistItem.Container`, not the `container` argument.

**V4 — pick a copyable audio stream** (`:996-1042`):
```
audioStreamWithSupportedCodec = first candidate stream whose Codec is in audioCodecs   // :996
channelsExceedsLimit = audioStreamWithSupportedCodec is not null
                       && Channels > (playlistItem.TranscodingMaxAudioChannels ?? int.MaxValue)   // :998
directAudioFailures  = audioStreamWithSupportedCodec is null ? 0
                       : GetCompatibilityAudioCodec(options, item, container ?? "",
                              audioStreamWithSupportedCodec, null, isVideo: true, isSecondaryAudio: false)  // :1000
playlistItem.TranscodeReasons |= directAudioFailures                                   // :1002
if audioStream is not null && audioStreamWithSupportedCodec is null:
    playlistItem.TranscodeReasons |= AudioCodecNotSupported                            // :1003-1006
directAudioStreamSatisfied = audioStreamWithSupportedCodec is not null
                             && !channelsExceedsLimit && directAudioFailures == 0      // :1008-1009
directAudioStreamSatisfied = directAudioStreamSatisfied
                             && !playlistItem.TranscodeReasons.HasFlag(ContainerBitrateExceedsLimit)  // :1011
directAudioStream = directAudioStreamSatisfied ? audioStreamWithSupportedCodec : null  // :1013
if channelsExceedsLimit && playlistItem.TargetAudioStream is not null:                 // :1015
    playlistItem.TranscodeReasons |= AudioChannelsNotSupported                          // :1017
    playlistItem.TargetAudioStream.Channels = playlistItem.TranscodingMaxAudioChannels  // :1018  <-- mutates the MediaStream
playlistItem.AudioCodecs = audioCodecs                                                 // :1021
if directAudioStream is not null:                                                      // :1022
    audioStream = directAudioStream                                                    // :1024  (local rebind — affects V6/V7)
    playlistItem.AudioStreamIndex = audioStream.Index                                  // :1025
    audioCodecs = [audioStream.Codec]; playlistItem.AudioCodecs = audioCodecs          // :1026-1027
    playlistItem.AudioSampleRate = audioStream.SampleRate                              // :1030
    SetOption(qualifier, "audiochannels", Channels?.ToString(Invariant) ?? "")          // :1031  <-- video-codec qualifier
    if audioStream.Profile non-empty: SetOption(audioStream.Codec, "profile", lowercased)  // :1033-1036
    if audioStream.Level is not null && != 0: SetOption(audioStream.Codec, "level", ...)   // :1038-1041
```
`:1018` mutates `MediaStream.Channels` on the source object — `TargetAudioStream` is
`MediaSource?.GetDefaultAudioStream(AudioStreamIndex)` (`StreamInfo.cs:289`), i.e. a stream inside
the `MediaSourceInfo` that gets serialized back to the client.

`:1031` uses `qualifier`, which is still `videoStream?.Codec` from `:958` — an *audio* channel
count stored under a *video* codec qualifier. Preserve it; the key spelling ends up in
`StreamOptions` and in `ToUrl`.

**V5 — gather condition inputs** (`:1044-1064`). All from `videoStream?.` except:
`videoFramerate = videoStream is null ? 0 : (videoStream.ReferenceFrameRate ?? 0)` (`:1051`, a
non-nullable `float`); `timestamp = videoStream is null ? TransportStreamTimestamp.None : item.Timestamp`
(`:1058`); `numStreams = item.MediaStreams.Count` (`:1062`, non-nullable `int`);
`numAudioStreams` / `numVideoStreams` from `item.GetStreamCount(...)` (`:1063-1064`), which
returns **null** when the source has zero streams of any kind
(`MediaSourceInfo.cs:222-242`).

**V6 — apply video codec profiles** (`:1066-1084`):
```
useSubContainer = playlistItem.SubProtocol == hls                                      // :1066
appliedVideoConditions = options.Profile.CodecProfiles
    .Where(i => i.Type == CodecType.Video
             && i.ContainsAnyCodec(playlistItem.VideoCodecs, container, useSubContainer)
             && i.ApplyConditions.All(c => ConditionProcessor.IsVideoConditionSatisfied(c, ...)))
    .Reverse()                                                                          // :1068-1073
foreach condition in appliedVideoConditions:                                            // :1074
    foreach transcodingVideoCodec in playlistItem.VideoCodecs:                          // :1076
        if condition.ContainsAnyCodec(transcodingVideoCodec, container, useSubContainer):
            ApplyTranscodingConditions(playlistItem, condition.Conditions, transcodingVideoCodec, true, true)
            continue                                                                    // :1081  <-- NOT break
```
`.Reverse()` is deliberate (`:1072` comment): the *first* codec profile has the highest priority,
so profiles are applied last-to-first and earlier ones overwrite later ones.

`:1081` is `continue`, not `break`. The equivalent audio loop at `:1113` uses `break`. So video
conditions are applied **once per matching codec** while audio conditions are applied **once per
profile**. See hazard H3.

**V7 — audio bitrate and audio codec profiles** (`:1087-1116`):
```
playlistItem.GlobalMaxAudioChannels = channelsExceedsLimit
        ? playlistItem.TranscodingMaxAudioChannels : options.MaxAudioChannels           // :1087
audioBitrate = GetAudioBitrate(options.GetMaxBitrate(true) ?? 0, playlistItem.TargetAudioCodec,
                               audioStream, playlistItem)                               // :1089
playlistItem.AudioBitrate = min(playlistItem.AudioBitrate ?? audioBitrate, audioBitrate)// :1090
isSecondaryAudio     = audioStream is null ? null : item.IsSecondaryAudio(audioStream)  // :1092
appliedAudioConditions = options.Profile.CodecProfiles
    .Where(i => i.Type == CodecType.VideoAudio
             && i.ContainsAnyCodec(playlistItem.AudioCodecs, container)   // note: no useSubContainer
             && i.ApplyConditions.All(c => IsVideoAudioConditionSatisfied(c, ...)))
    .Reverse()                                                                          // :1099-1104
foreach codecProfile in appliedAudioConditions:
    foreach transcodingAudioCodec in playlistItem.AudioCodecs:
        if codecProfile.ContainsAnyCodec(transcodingAudioCodec, container):
            ApplyTranscodingConditions(playlistItem, codecProfile.Conditions, transcodingAudioCodec, true, true)
            break                                                                        // :1113
```
`audioStream` here is the possibly-rebound local from `:1024`.

`IsSecondaryAudio` (`MediaSourceInfo.cs:244-260`): `false` if the stream is external; else compare
the index of the first non-external audio stream — `true` when they differ; `null` if there are
no non-external audio streams.

**V8 — video bitrate clamp** (`:1118-1133`):
```
maxBitrateSetting = options.GetMaxBitrate(false)
if maxBitrateSetting.HasValue:
    availableBitrateForVideo = maxBitrateSetting.Value
    if playlistItem.AudioBitrate.HasValue: availableBitrateForVideo -= AudioBitrate      // :1124-1127
    currentValue = playlistItem.VideoBitrate ?? availableBitrateForVideo                 // :1131
    playlistItem.VideoBitrate = max(min(availableBitrateForVideo, currentValue), 64_000) // :1132
```
The floor of 64,000 is applied after the min, deliberately not `Math.Clamp` (`:1129-1130`
comment) — `availableBitrateForVideo` may legitimately be below 64k and the result is still 64k.

### 2.6 Audio bitrate helpers

`GetAudioBitrate(maxTotalBitrate, targetAudioCodecs, audioStream, item)` (`:1178-1231`):
```
targetAudioCodec    = targetAudioCodecs.Count == 0 ? null : targetAudioCodecs[0]        // :1180
targetAudioChannels = item.GetTargetAudioChannels(targetAudioCodec)                     // :1182
encoderAudioBitrateLimit = int.MaxValue
if audioStream is null:
    defaultBitrate = 192000                                                             // :1189
else:
    if targetAudioChannels.HasValue && audioStream.Channels.HasValue
       && audioStream.Channels > targetAudioChannels:                                   // :1193-1195
        defaultBitrate = GetDefaultAudioBitrate(targetAudioCodec, targetAudioChannels)  // :1198
    elif targetAudioChannels.HasValue && audioStream.Channels.HasValue
       && audioStream.Channels <= targetAudioChannels
       && audioStream.Codec non-empty && targetAudioCodecs is not null
       && targetAudioCodecs.Count > 0
       && !targetAudioCodecs.Any(e => e == audioStream.Codec, ordinal-ignore-case):     // :1200-1206
        defaultBitrate = GetDefaultAudioBitrate(targetAudioCodec, audioStream.Channels) // :1209
    else:
        defaultBitrate = audioStream.BitRate ?? GetDefaultAudioBitrate(targetAudioCodec, targetAudioChannels)  // :1213
    if audioStream.Channels == 1 && (audioStream.BitRate ?? 0) < 64000:
        encoderAudioBitrateLimit = 64000                                                // :1218-1222
if maxTotalBitrate > 0:
    defaultBitrate = min(GetMaxAudioBitrateForTotalBitrate(maxTotalBitrate), defaultBitrate)  // :1225-1228
return min(defaultBitrate, encoderAudioBitrateLimit)                                    // :1230
```

`GetDefaultAudioBitrate(audioCodec, audioChannels)` (`:1145-1176`):
- `aac`/`mp3`/`ac3`/`eac3` (ordinal-ignore-case): `<2` channels → 128000; `>=6` → 640000; else 384000 (`:1150-1161`)
- `flac`/`alac`: `<2` → 768000; `>=6` → 3584000; else 1536000 (`:1163-1172`)
- otherwise (including null/empty codec) → 192000 (`:1175`)

Channel comparisons use `audioChannels ?? 0`, so an unknown channel count takes the `<2` branch.

`GetMaxAudioBitrateForTotalBitrate(totalBitrate)` (`:1233-1276`) — inclusive upper bounds:

| `totalBitrate <=` | result |
|--:|--:|
| 640000 | 128000 |
| 2000000 | 384000 |
| 3000000 | 448000 |
| 4000000 | 640000 |
| 5000000 | 768000 |
| 10000000 | 1536000 |
| 15000000 | 2304000 |
| 20000000 | 3584000 |
| *(else)* | 7168000 |

`StreamInfo.GetTargetAudioChannels(codec)` (`StreamInfo.cs:1360-1376`):
`defaultValue = GlobalMaxAudioChannels ?? TranscodingMaxAudioChannels`; look up
`GetOption(codec, "audiochannels")`; empty → `defaultValue`; parseable → `min(parsed, defaultValue ?? parsed)`;
unparseable → `defaultValue`.

`StreamInfo.GetOption(qualifier, name)` (`StreamInfo.cs:843-853`): try `qualifier + "-" + name`
first, fall back to bare `name`. Note that when `qualifier` is null the first lookup key is
literally `"-name"`, which normally misses and falls through. `SetOption(qualifier, name, value)`
(`:815-825`) writes the bare `name` when the qualifier is empty, otherwise `qualifier + "-" + name`.
The port must reproduce the `-` separator exactly; these keys reach the wire through `ToUrl`.

---

## 3. `GetVideoDirectPlayProfile` (`:1278`) — exact check ordering

Signature returns `(DirectPlayProfile? Profile, PlayMethod? PlayMethod, int? AudioStreamIndex, TranscodeReason TranscodeReasons)`.

### 3.1 Force short-circuits (`:1288-1296`)

**First thing in the function**, before any profile is examined:
```
if options.ForceDirectPlay:   return (null, DirectPlay,   audioStream?.Index, 0)      // :1288-1291
if options.ForceDirectStream: return (null, DirectStream, audioStream?.Index, 0)      // :1293-1296
```
`Profile` is **null** and reasons are **0**. The caller therefore gets
`directPlayProfile = null`, so `:745` normalizes the container against *all* direct-play
profiles, and `:766`/`:770` pass `null` container/codecs into the direct-stream branch.

### 3.2 Once-computed reason sets (`:1298-1322`)

Computed **once**, outside the per-profile loop, in this order:

1. `container = mediaSource.Container` (`:1299`).
2. `containerProfileReasons = GetCompatibilityContainer(options, mediaSource, container, videoStream)` (`:1302`).
3. `videoCodecProfileReasons = videoStream is null ? 0 : GetCompatibilityVideoCodec(options, mediaSource, container, videoStream)` (`:1305`).
4. `audioStreamMatches` = a dictionary keyed by each candidate audio stream, value
   `GetCompatibilityAudioCodecDirect(options, mediaSource, container, audioStream, isVideo: true, isSecondaryAudio: mediaSource.IsSecondaryAudio(audioStream) ?? false)` (`:1308`).
   `ToDictionary` throws on duplicate keys — reference identity, so duplicates cannot occur from
   a well-formed `MediaStreams` list.
5. `subtitleProfileReasons` (`:1310-1322`): `0` when `subtitleStream is null`; otherwise call
   `GetSubtitleProfile(mediaSource, subtitleStream, options.Profile.SubtitleProfiles,
   PlayMethod.DirectPlay, _transcoderSupport, container, transcodingSubProtocol: null)` and set
   `SubtitleCodecNotSupported` when the resulting `Method` is **not** `Drop`, **not** `External`
   and **not** `Embed` (`:1315-1317`) — i.e. when it is `Encode` or `Hls`.

Note the `PlayMethod.DirectPlay` argument at `:1313` is fixed; the subtitle decision used to veto
direct play is computed as if direct play were happening.

### 3.3 Loop preamble (`:1324-1325`)

```
containerSupported = false                                                                    // :1324
rankings = [VideoCodecNotSupported, VideoCodecReasons, AudioCodecNotSupported,
            AudioCodecReasons, ContainerReasons]                                              // :1325
```

`containerSupported` is a captured local mutated **inside** the LINQ `Select` below. See §8.2
and hazard H4.

### 3.4 Per-profile body (`:1328-1394`)

Source: `profile.DirectPlayProfiles.Where(Type == Video).Select((directPlayProfile, order) => ...)`
(`:1328-1330`). `order` is the index **within the filtered sequence**, not within the original
array. Client-supplied order is preserved and reused as the final tiebreak.

For each profile, in order:

```
directPlayProfileReasons = 0
audioCodecProfileReasons = 0                                                     // :1332-1333

// 1. container
if !directPlayProfile.SupportsContainer(container):
    directPlayProfileReasons |= ContainerNotSupported                            // :1336-1339
else:
    containerSupported = true                                                    // :1340-1343

// 2. video codec
videoCodec = videoStream?.Codec                                                  // :1346
if !directPlayProfile.SupportsVideoCodec(videoCodec):
    directPlayProfileReasons |= VideoCodecNotSupported                           // :1347-1350

// 3. audio codec
selectedAudioStream = null
if candidateAudioStreams.Count != 0:                                             // :1354
    selectedAudioStream = first candidate whose Codec this profile supports      // :1356
    if selectedAudioStream is null:
        directPlayProfileReasons |= AudioCodecNotSupported                       // :1357-1360
    else:
        audioCodecProfileReasons = audioStreamMatches[selectedAudioStream]       // :1363
                                   (GetValueOrDefault → 0 if absent)
```

When `candidateAudioStreams` is empty, no audio reason is produced at all and
`selectedAudioStream` stays null — the returned `AudioStreamIndex` is then null and the caller
falls back to `audioStream?.Index` at `:753`.

`SupportsVideoCodec(null)` → `ContainsContainer(VideoCodec, (string?)null)`. That routes to the
`string?` three-argument overload (`ContainerHelper.cs:63-71`), whose **first** check is
`if (string.IsNullOrEmpty(inputContainer)) return isNegativeList;` (`:65-68`) — it returns
`false` *before* the "empty profile supports everything" rule at `:84-88` can apply. Practical
effect: **a media source with no video stream fails `SupportsVideoCodec` against every profile**,
including profiles that declare no `VideoCodec` at all, so every profile accumulates
`VideoCodecNotSupported`. The empty-profile rule only helps when the *input* codec is non-empty.

### 3.5 Reason composition and codec masking (`:1367-1377`)

```
failureReasons = directPlayProfileReasons | containerProfileReasons | subtitleProfileReasons   // :1367

if (failureReasons & VideoCodecNotSupported) == 0:
    failureReasons |= videoCodecProfileReasons                                                 // :1369-1372

if (failureReasons & AudioCodecNotSupported) == 0:
    failureReasons |= audioCodecProfileReasons                                                 // :1374-1377
```

This is the **codec-reason masking**. The fine-grained codec-condition reasons
(`VideoProfileNotSupported`, `AudioChannelsNotSupported`, …) are added **only when the coarse
codec-not-supported bit is clear**. If the profile already rejected the codec outright, the
per-condition detail is suppressed.

Two consequences that a "cleaner" implementation loses:
- The mask is tested against `failureReasons` *after* the container/subtitle bits are folded in
  — but neither of those can set a codec bit, so testing `directPlayProfileReasons` would be
  equivalent today. Transliterate the written form anyway; it is what the corpus pins.
- The masking is per-profile, so the same media source produces different reason sets against
  different `DirectPlayProfile` entries. Which one surfaces depends on the sort (§3.7).

### 3.6 Direct-play vs direct-stream (`:1379-1389`)

```
directStreamFailureReasons = failureReasons & (~DirectStreamReasons)                           // :1379

playMethod = null
if failureReasons == 0 && isEligibleForDirectPlay && mediaSource.SupportsDirectPlay:
    playMethod = DirectPlay                                                                    // :1382-1385
elif directStreamFailureReasons == 0 && isEligibleForDirectStream && mediaSource.SupportsDirectStream:
    playMethod = DirectStream                                                                  // :1386-1389
```

`:1379` **is** the direct-play/direct-stream distinction. `DirectStreamReasons` (§1.2) enumerates
exactly the failures remuxing can fix: any audio problem, a container mismatch, and a video codec
*tag* mismatch. Everything else — video codec, video profile/level/resolution/framerate/bitdepth/
range/rotation, subtitle, bitrate-exceeds-limit, stream count — survives the mask and blocks
direct stream too.

Note `ContainerBitrateExceedsLimit` is **not** in `DirectStreamReasons`, but it also cannot be
set inside this function (§3.9), so it never blocks direct stream from here. It is added by the
caller at `:723` and only affects eligibility via `:711-712`.

### 3.7 Rank and sort (`:1391-1399`)

```
ranked = GetRank(ref failureReasons, rankings)                                                 // :1391
return (Result: (Profile, PlayMethod, AudioStreamIndex: selectedAudioStream?.Index,
                 TranscodeReason: failureReasons), Order: order, Rank: ranked)                 // :1393
```

`GetRank` (`:2325-2340`):
```
index = 1
foreach flag in rankings:
    if (a & flag) != 0: return index
    index++
return index                      // == rankings.Length + 1 == 6 when nothing matches
```
The `ref` parameter is **never written**. Port it by value.

Rank semantics: **lower rank = more severe failure**, because `rankings` is ordered most-severe
first. Rank 1 = video codec unsupported; rank 6 = no ranked failure at all.

The sort (`:1395-1399`):
```
.OrderByDescending(analysis => analysis.Result.PlayMethod)     // :1395
.ThenByDescending(analysis => analysis.Rank)                   // :1396
.ThenBy(analysis => analysis.Order)                            // :1397
.ToArray()                                                     // :1398
.ToLookup(analysis => analysis.Result.PlayMethod is not null)  // :1399
```

- Key 1 descending on `PlayMethod?`: C# orders `null` **below** every value, so descending puts
  non-null first, then `DirectPlay`(2) > `DirectStream`(1) > `Transcode`(0).
- Key 2 descending on rank: prefers the *least severe* failure set.
- Key 3 ascending on `Order`: **client-supplied profile order is the final tiebreak.** Preserve
  it exactly.
- `.ToArray()` forces enumeration (§8.2).
- `.ToLookup` partitions into "has a play method" / "does not", preserving the sorted order
  within each bucket.

### 3.8 Result selection (`:1401-1418`)

```
profileMatch = analyzedProfiles[true].Select(a => a.Result).FirstOrDefault()                   // :1401-1403
if profileMatch.Profile is not null: return profileMatch                                       // :1404-1407

failureReasons = analyzedProfiles[false].Select(a => a.Result)
    .Where(r => !containerSupported || !r.TranscodeReason.HasFlag(ContainerNotSupported))      // :1411
    .FirstOrDefault().TranscodeReason                                                          // :1409-1412
if failureReasons == 0: failureReasons = DirectPlayError                                       // :1413-1416
return (null, null, null, failureReasons)                                                      // :1418
```

The `:1411` filter: **if any profile matched the container**, profiles that failed *on* the
container are excluded from the explanation. So the reported reason describes a
container-compatible profile's failure, not a container mismatch. The `FirstOrDefault` on an
empty filtered sequence yields the default tuple with `TranscodeReason = 0`, which is then
replaced by `DirectPlayError` (`:1415`).

`DirectPlayError` is therefore emitted in exactly two situations: no video `DirectPlayProfile`
entries at all, or every failing profile was filtered out by `:1411`.

### 3.9 Compatibility helpers

All four funnel through `AggregateFailureConditions` (`:1421-1429`), which folds `|` over
`GetTranscodeReasonForFailedCondition(condition)` for every **failing** condition, logging each
(`:1423-1428`). Empty sequence → `0`.

`GetTranscodeReasonForFailedCondition` (`:305-396`) — the property→bit map:

| Property | Reason bit | Line |
|:--|:--|--:|
| `AudioBitrate` | `AudioBitrateNotSupported` | :310 |
| `AudioChannels` | `AudioChannelsNotSupported` | :313 |
| `AudioProfile` | `AudioProfileNotSupported` | :316 |
| `AudioSampleRate` | `AudioSampleRateNotSupported` | :319 |
| `Has64BitOffsets` | **0** (TODO) | :322-323 |
| `Height` | `VideoResolutionNotSupported` | :326 |
| `IsAnamorphic` | `AnamorphicVideoNotSupported` | :329 |
| `IsAvc` | **0** (TODO) | :332-333 |
| `IsInterlaced` | `InterlacedVideoNotSupported` | :336 |
| `IsSecondaryAudio` | `SecondaryAudioNotSupported` | :339 |
| `NumStreams` | `StreamCountExceedsLimit` | :342 |
| `NumAudioStreams` | **0** (TODO) | :345-346 |
| `NumVideoStreams` | **0** (TODO) | :349-350 |
| `PacketLength` | **0** (TODO) | :353-354 |
| `RefFrames` | `RefFramesNotSupported` | :357 |
| `VideoBitDepth` | `VideoBitDepthNotSupported` | :360 |
| `AudioBitDepth` | `AudioBitDepthNotSupported` | :363 |
| `VideoBitrate` | `VideoBitrateNotSupported` | :366 |
| `VideoCodecTag` | `VideoCodecTagNotSupported` | :369 |
| `VideoFramerate` | `VideoFramerateNotSupported` | :372 |
| `VideoLevel` | `VideoLevelNotSupported` | :375 |
| `VideoProfile` | `VideoProfileNotSupported` | :378 |
| `VideoRangeType` | `VideoRangeTypeNotSupported` | :381 |
| `VideoRotation` | `VideoRotationNotSupported` | :384 |
| `VideoTimestamp` | **0** (TODO) | :387-388 |
| `Width` | `VideoResolutionNotSupported` | :391 |
| *(default)* | **0** | :393-394 |

Six properties map to **zero**: `Has64BitOffsets`, `IsAvc`, `NumAudioStreams`, `NumVideoStreams`,
`PacketLength`, `VideoTimestamp`. A condition on any of them can fail and contribute no bit;
since `failureReasons |= 0` is a no-op, such a failure is invisible and **does not block direct
play**. `Width` and `Height` both collapse onto `VideoResolutionNotSupported`.

`CheckVideoConditions(conditions, mediaSource, videoStream)` (`:2349-2374`) gathers the same 19
inputs as V5 and returns the conditions where `IsVideoConditionSatisfied` is **false**.

`GetCompatibilityContainer` (`:2384-2397`): over `profile.ContainerProfiles` where
`Type == Video` and `ContainsContainer(container)` (no sub-container), `SelectMany` the failing
conditions, aggregate. Log type string is `"VideoCodecProfile"` (`:2391`) — a copy-paste in the
original; log-only.

`GetCompatibilityVideoCodec` (`:2407-2424`): over `profile.CodecProfiles` where
`Type == CodecType.Video`, `ContainsAnyCodec(videoCodec, container)` (no sub-container), **and**
`!CheckVideoConditions(codecProfile.ApplyConditions, ...).Any()` — i.e. every `ApplyCondition`
satisfied — `SelectMany` the failing `Conditions`, aggregate.

`GetCompatibilityAudioCodec(options, mediaSource, container, audioStream, transcodingAudioCodec, isVideo, isSecondaryAudio)`
(`:2437-2455`): `audioCodec = transcodingAudioCodec ?? audioStream.Codec` (`:2441`); when
`isVideo` use `GetProfileConditionsForVideoAudio` (`:1698-1715`), else
`GetProfileConditionsForAudio(..., checkConditions: true)` (`:1717-1739`); aggregate.

- `GetProfileConditionsForVideoAudio`: `CodecProfiles` where `Type == VideoAudio` and
  `ContainsAnyCodec(codec, container)` and all `ApplyConditions` satisfied → `SelectMany(Conditions)`
  → keep the **unsatisfied** ones.
- `GetProfileConditionsForAudio`: same shape with `Type == CodecType.Audio` and
  `IsAudioConditionSatisfied`; when `checkConditions` is false it returns **all** conditions
  without filtering (`:1733-1736`) — used by the audio transcode path (§4.6).

`GetCompatibilityAudioCodecDirect` (`:2467-2477`): `GetCompatibilityAudioCodec(..., transcodingAudioCodec: null, ...)`
then `|= AudioIsExternal` when `audioStream.IsExternal` (`:2471-2474`). Only this wrapper ever
sets `AudioIsExternal`.

**No path inside `GetVideoDirectPlayProfile` can set `ContainerBitrateExceedsLimit`** — it is not
produced by `GetTranscodeReasonForFailedCondition` and not set literally anywhere in `:1278-1419`.

---

## 4. Audio path — control flow

`analysis/03` covered the video path only. This section is built from source.

### 4.1 `GetOptimalAudioStream(MediaOptions)` (`:51`)

1. `ValidateMediaOptions(options, isMediaSource: false)` (`:53`). **Note the `false`** — the
   `MediaSourceId`-required checks at `:1684-1695` are skipped for audio, so an audio request may
   set `AudioStreamIndex`/`SubtitleStreamIndex` without a `MediaSourceId` and will not throw.
2. Loop over `options.MediaSources` **with an inline filter** rather than a LINQ `Where`
   (`:56-62`): skip unless `MediaSourceId` is empty or `mediaSource.Id` matches
   ordinal-case-insensitively.
3. For each surviving source: `streamInfo = GetOptimalAudioStream(mediaSource, options)` (`:64`);
   if non-null, stamp `DeviceId` and `DeviceProfileId` **immediately** (`:67-68`) — unlike the
   video path, which stamps after the loop — and append (`:69`).
4. `return GetOptimalStream(streams, options.GetMaxBitrate(true) ?? 0)` (`:73`). Note
   `isAudio: true`, so `MaxStaticMusicBitrate` can apply.

The private overload **can return null** (`:181`), so the audio list may be shorter than the
source list.

### 4.2 `GetOptimalAudioStream(MediaSourceInfo, MediaOptions)` (`:76`) — the per-source builder

**Step A — construct** (`:78-86`): `ItemId`, `MediaType = Audio`, `MediaSource = item`,
`RunTimeTicks`, `Context`, `DeviceProfile`. No subtitle index, no
`AlwaysBurnInSubtitleWhenTranscoding`.

**Step B — force short-circuits** (`:88-100`), before anything else is examined:
```
if options.ForceDirectPlay:
    PlayMethod = DirectPlay
    Container  = NormalizeMediaSourceFormatIntoSingleContainer(item.Container, options.Profile, Audio)   // playProfile = null
    return                                                                              // :88-93
if options.ForceDirectStream:
    PlayMethod = DirectStream
    Container  = NormalizeMediaSourceFormatIntoSingleContainer(item.Container, options.Profile, Audio)
    return                                                                              // :95-100
```
`TranscodeReasons` is left at its default (0) on both returns. `SubProtocol` is left at its
default. Nothing else is populated.

**Step C — resolve the audio stream** (`:102-104`):
`audioStream = item.GetDefaultAudioStream(null)` — always `null` as the requested index, so it
is "first `IsDefault` audio stream, else first audio stream". `options.AudioStreamIndex` is
**ignored on the audio path.** Then `ArgumentNullException.ThrowIfNull(audioStream)` — an audio
media source with no audio stream **throws**, it does not return null.

**Step D — direct play profile** (`:106-109`):
`directPlayInfo = GetAudioDirectPlayProfile(item, audioStream, options)` (§4.3);
`directPlayMethod = directPlayInfo.PlayMethod`; `transcodeReasons = directPlayInfo.TranscodeReasons`.

### 4.3 `GetAudioDirectPlayProfile` (`:435`)

Returns `(DirectPlayProfile? Profile, PlayMethod? PlayMethod, TranscodeReason TranscodeReasons)`.

**Step 1 — find a direct-play profile** (`:437-438`): first `DirectPlayProfile` with
`Type == Audio` satisfying `IsAudioDirectPlaySupported` (`:2292-2307`):
- `IsAudioContainerSupported(profile, item)` (`:2277-2290`) — `profile.SupportsContainer(item.Container)`,
  **and** additionally `!ContainsContainer("mkv", item.Container) || profile.SupportsContainer("mkv")`.
  That second clause exists because a webm-only profile would otherwise accept matroska
  (`:2285-2289`, jellyfin#13344). Note the argument order: `ContainsContainer("mkv", item.Container)`
  treats `"mkv"` as the *profile* list and the item container as the *input*.
- **and** `profile.SupportsAudioCodec(audioStream?.Codec)`.

**Step 2 — direct-stream fallback** (`:441-461`). If no direct-play profile matched, log, then
look for the first `Type == Audio` profile satisfying `IsAudioDirectStreamSupported`
(`:2309-2323`):
- `IsAudioContainerSupported(profile, item)` must be **false** (`:2313-2316`) — the container must
  *not* be supported, otherwise the file would have direct-played.
- **and** (`profile.AudioCodec == audioStream?.Codec` ordinal-ignore-case **or**
  `profile.Container == audioStream?.Codec` ordinal-ignore-case) — a strict string equality, not
  `SupportsAudioCodec`, deliberately, because the latter treats an empty container as
  all-supported (`:2318-2320` comment).

If found: `directPlayProfile = directStreamProfile` and `transcodeReasons |= ContainerNotSupported`
(`:454-455`). If not found: **return immediately** with
`(null, null, GetTranscodeReasonsFromDirectPlayProfile(item, videoStream: null, audioStream, options.Profile.DirectPlayProfiles))`
(`:459`).

**Step 3 — direct-play gate** (`:467-480`):
```
if item.SupportsDirectPlay && transcodeReasons == 0:                      // :467
    if !IsBitrateLimitExceeded(item, options.GetMaxBitrate(true) ?? 0):   // :469
        if options.EnableDirectPlay:                                      // :471
            return (directPlayProfile, DirectPlay, 0)                     // :473
    else:
        transcodeReasons |= ContainerBitrateExceedsLimit                  // :478
```
`transcodeReasons == 0` is what makes the direct-stream fallback (which set
`ContainerNotSupported`) skip this whole block — including the bitrate check.

**Step 4 — direct-stream gate** (`:483-499`):
```
if item.SupportsDirectStream:                                             // :483
    if !IsBitrateLimitExceeded(item, options.GetMaxBitrate(true) ?? 0):   // :485
        if transcodeReasons == ContainerNotSupported:                     // :490  (equality, not HasFlag)
            return (directPlayProfile, DirectStream, transcodeReasons)    // :492
    else:
        transcodeReasons |= ContainerBitrateExceedsLimit                  // :497
```
`options.EnableDirectStream` is deliberately **not** consulted here (`:487-489` comment: it is
always false in the 10.10 codebase because HTTP direct-stream is broken, and audio is assumed to
support it).

The `:490` test is exact equality with `ContainerNotSupported`. If the bitrate limit was also
exceeded, `transcodeReasons` would be `ContainerNotSupported | ContainerBitrateExceedsLimit` — but
that combination is unreachable, since the `|=` at `:497` happens only in the `else` branch where
the direct-stream return is already skipped.

**Step 5 — fall through** (`:501`): `return (directPlayProfile, null, transcodeReasons)`.

The notable fall-through: a profile matched, `transcodeReasons == 0`, but
`options.EnableDirectPlay` is false. Step 4's `:490` test then fails (0 ≠ `ContainerNotSupported`),
so the function returns `(profile, null, 0)` — **a transcode with an empty `TranscodeReasons`.**
See hazard H10.

`GetTranscodeReasonsFromDirectPlayProfile` (`:504-547`), reached only from `:459`:
```
mediaType = videoStream is null ? Audio : Video          // :506  (always Audio here)
containerSupported = audioSupported = videoSupported = false          // :508-510
foreach profile in directPlayProfiles:                                // :512
    if profile.Type == mediaType && profile.SupportsContainer(item.Container):
        containerSupported = true
        videoSupported = videoStream is null || profile.SupportsVideoCodec(videoStream.Codec)
        audioSupported = audioStream is null || profile.SupportsAudioCodec(audioStream.Codec)
        if videoSupported && audioSupported: break                     // :523-526
reasons = 0
if !containerSupported: reasons |= ContainerNotSupported               // :531-534
if !videoSupported:     reasons |= VideoCodecNotSupported              // :536-539
if !audioSupported:     reasons |= AudioCodecNotSupported              // :541-544
```
Two behaviours to preserve exactly:
- `videoSupported`/`audioSupported` are **assigned, not OR-ed**, inside the loop, so their final
  values come from the **last** container-matching profile examined (unless the loop broke early),
  not from a union across profiles.
- If **no** profile matches the container, both stay `false` from initialization, so an *audio*
  item emits `ContainerNotSupported | VideoCodecNotSupported | AudioCodecNotSupported` — a
  video-codec bit on an audio stream. See hazard H11.

### 4.4 Direct-play branch in the builder (`:111-123`)

```
if directPlayMethod is DirectPlay:
    audioFailureReasons = GetCompatibilityAudioCodec(options, item, item.Container, audioStream,
                                                     transcodingAudioCodec: null,
                                                     isVideo: false, isSecondaryAudio: false)   // :113
    transcodeReasons |= audioFailureReasons                                                     // :114
    if audioFailureReasons == 0:                                                                // :116
        playlistItem.PlayMethod = DirectPlay
        playlistItem.Container  = NormalizeMediaSourceFormatIntoSingleContainer(
                                      item.Container, options.Profile, Audio, directPlayInfo.Profile)  // :119
        return playlistItem                                                                     // :121
```
`isVideo: false` routes to `GetProfileConditionsForAudio` → `IsAudioConditionSatisfied`, which
handles only four properties and **throws** on anything else (§5.1). `TranscodeReasons` is not
assigned on this return; it stays at its default 0, which is correct only because
`directPlayInfo.TranscodeReasons` is 0 on the direct-play return path (`:473`).

If `audioFailureReasons != 0`, control falls through. `directPlayMethod` is `DirectPlay`, so the
`:125` direct-stream branch is **not** taken — audio codec-condition failures go straight to
transcoding.

### 4.5 Direct-stream branch in the builder (`:125-163`)

```
remuxContainer = item.TranscodingContainer ?? "ts"                                          // :127
supportedHlsContainers = ["ts", "mp4"]                                                      // :128
if directPlayInfo.Profile?.Container is one of supportedHlsContainers (ordinal-ignore-case):
    remuxContainer = directPlayInfo.Profile?.Container                                      // :131
if item.TranscodingSubProtocol == hls:                                                      // :133
    if remuxContainer == "mp4" (ordinal-ignore-case):
        codeIsSupported = _supportedHlsAudioCodecsMp4.Contains(
                              directPlayInfo.Profile?.AudioCodec ?? directPlayInfo.Profile?.Container)   // :138
    else:
        codeIsSupported = _supportedHlsAudioCodecsTs.Contains(...)                          // :142
else:
    codeIsSupported = true                                                                  // :148
if codeIsSupported:                                                                         // :151
    playlistItem.PlayMethod       = DirectStream
    playlistItem.Container        = remuxContainer
    playlistItem.TranscodeReasons = transcodeReasons
    playlistItem.SubProtocol      = item.TranscodingSubProtocol
    item.TranscodingContainer     = remuxContainer          // :157  <-- mutates the media source
    return playlistItem                                                                     // :158
transcodeReasons |= AudioCodecNotSupported                                                  // :161
playlistItem.TranscodeReasons = transcodeReasons                                            // :162
```

Notes:
- `Array.Exists` at `:131` compares against `directPlayInfo.Profile?.Container`; when that is
  null, no match, and `remuxContainer` keeps the `TranscodingContainer ?? "ts"` value.
- The HLS allowlist check at `:138`/`:142` tests `AudioCodec ?? Container` of the *profile*, not
  the actual stream codec, and uses `List.Contains` — **ordinal case-sensitive**, unlike almost
  every other comparison in this file. A profile declaring `AAC` (uppercase) fails the check.
- `:162` sets `TranscodeReasons` before falling into the transcode section, and `:221` sets it
  again at the end — the second assignment uses the same local, so the value is identical.

### 4.6 Transcode section (`:165-222`)

```
transcodingProfile = first tcProfile in options.Profile.TranscodingProfiles where
      tcProfile.Type == playlistItem.MediaType (Audio)
   && tcProfile.Context == options.Context
   && _transcoderSupport.CanEncodeToAudioCodec(tcProfile.AudioCodec ?? tcProfile.Container)   // :166-175
```
A plain `foreach`/`break`, so the **first** match in client order wins — no ranking, unlike the
video path.

If a profile was found (`:177`):
1. `if !item.SupportsTranscoding: return null` (`:179-182`) — this is the only null return of the
   whole audio builder, and it happens **after** a transcoding profile was already selected.
2. `SetStreamInfoOptionsFromTranscodingProfile(item, playlistItem, transcodingProfile)` (`:184`).
   `playlistItem.PlayMethod` is still the default `Transcode` (0) here — unless the direct-stream
   branch fell through at `:161-162`, in which case it is *also* still `Transcode`, because
   `:153` only runs on the `codeIsSupported` path. So the `:600` guard always passes and
   `Container`/`SubProtocol` are set from the transcoding profile.
3. `audioTranscodingConditions = GetProfileConditionsForAudio(options.Profile.CodecProfiles,
   transcodingProfile.Container, transcodingProfile.AudioCodec, inputAudioChannels,
   inputAudioBitrate, inputAudioSampleRate, inputAudioBitDepth, checkConditions: false).ToArray()`
   (`:186-191`). **`checkConditions: false`** — every condition of every matching codec profile is
   returned, satisfied or not (`:1733-1736`). Then
   `ApplyTranscodingConditions(playlistItem, audioTranscodingConditions, qualifier: null, true, true)`
   (`:192`).
4. `playlistItem.GlobalMaxAudioChannels = options.MaxAudioChannels` (`:195`).
5. Bitrate (`:197-210`):
   ```
   configuredBitrate = options.GetMaxBitrate(true)
   transcodingBitrate = options.AudioTranscodingBitrate
                     ?? (options.Context == Streaming ? options.Profile.MusicStreamingTranscodingBitrate : null)
                     ?? configuredBitrate
                     ?? 128000
   if configuredBitrate.HasValue: transcodingBitrate = min(configuredBitrate, transcodingBitrate)
   longBitrate = min(transcodingBitrate, playlistItem.AudioBitrate ?? transcodingBitrate)
   playlistItem.AudioBitrate = longBitrate > int.MaxValue ? int.MaxValue : (int)longBitrate
   ```
   `transcodingBitrate` is a `long`; the saturation at `int.MaxValue` is explicit.
6. `if playlistItem.AudioCodecs.Count == 0 && transcodingProfile.AudioCodec is non-whitespace:
   playlistItem.AudioCodecs = [transcodingProfile.AudioCodec]` (`:215-218`). Comma-separated
   transcoding audio codecs are deliberately **not** split here (`:212-214` comment).

Finally `playlistItem.TranscodeReasons = transcodeReasons; return playlistItem` (`:221-222`).

If **no** transcoding profile matched, the whole block is skipped and the item is returned with
`PlayMethod = Transcode` (default), no container, no codecs, and whatever reasons accumulated.

### 4.7 Audio-path summary table

| Situation | `PlayMethod` | `Container` | `TranscodeReasons` | Return line |
|:--|:--|:--|:--|--:|
| `ForceDirectPlay` | `DirectPlay` | normalized source | 0 (default) | :92 |
| `ForceDirectStream` | `DirectStream` | normalized source | 0 (default) | :99 |
| direct play, no codec-condition failures | `DirectPlay` | normalized w/ profile | 0 (default) | :121 |
| direct stream, HLS codec ok | `DirectStream` | `remuxContainer` | from `GetAudioDirectPlayProfile` | :158 |
| `!item.SupportsTranscoding` after profile match | — | — | — | `null` @ :181 |
| transcode | `Transcode` | transcoding profile | accumulated | :222 |
| no transcoding profile | `Transcode` (default) | unset | accumulated | :222 |

---

## 5. ProfileCondition evaluation — `ConditionProcessor.cs`

### 5.1 Four disjoint entry points

| Entry point | Line | Properties handled |
|:--|--:|:--|
| `IsVideoConditionSatisfied` | :38 | 19: `IsInterlaced`, `IsAnamorphic`, `IsAvc`, `VideoFramerate`, `VideoLevel`, `VideoProfile`, `VideoRangeType`, `VideoCodecTag`, `PacketLength`, `VideoBitDepth`, `VideoBitrate`, `Height`, `Width`, `RefFrames`, `NumStreams`, `NumAudioStreams`, `NumVideoStreams`, `VideoTimestamp`, `VideoRotation` (:62-99) |
| `IsImageConditionSatisfied` | :112 | 2: `Height`, `Width` (:116-119) |
| `IsAudioConditionSatisfied` | :134 | 4: `AudioBitrate`, `AudioChannels`, `AudioSampleRate`, `AudioBitDepth` (:138-145) |
| `IsVideoAudioConditionSatisfied` | :162 | 6: `AudioProfile`, `AudioBitrate`, `AudioChannels`, `IsSecondaryAudio`, `AudioSampleRate`, `AudioBitDepth` (:173-184) |

**`Has64BitOffsets` is handled by no entry point.**

**Unhandled-property behaviour is NOT uniform. This corrects the framing in the task brief and in
`analysis/03`:**

- `IsVideoConditionSatisfied` — `default: return true` (`:100-101`). Permissive.
- `IsImageConditionSatisfied` — `default: throw new ArgumentException("Unexpected condition on image file: " + condition.Property)` (`:120-122`).
- `IsAudioConditionSatisfied` — `default: throw new ArgumentException("Unexpected condition on audio file: " + ...)` (`:146-148`).
- `IsVideoAudioConditionSatisfied` — `default: throw new ArgumentException("Unexpected condition on audio file: " + ...)` (`:185-187`).

Only the video entry point is permissive. The other three **throw**, which surfaces as a 500 from
`PlaybackInfo`. Consequence: a client `CodecProfile` of `Type = Audio` or `VideoAudio` carrying,
say, a `Width` condition crashes the audio compatibility check at `:2450`/`:2449`. The Go port
must produce the same failure (an error that propagates to a 500), not silently return `true`.

### 5.2 Typed comparators

Dispatch is by the C# static type of the value passed at the call site, not by the property:

| Property | Comparator overload | Line |
|:--|:--|--:|
| `IsInterlaced`, `IsAnamorphic`, `IsAvc`, `IsSecondaryAudio` | `bool?` | :256 |
| `VideoFramerate` | `double?` — **the `float?` argument is widened** | :280 |
| `VideoLevel` | `double?` | :280 |
| `VideoProfile`, `VideoCodecTag`, `AudioProfile` | `string?` | :233 |
| `VideoRangeType` | `VideoRangeType?` | :344 |
| `VideoTimestamp` | `TransportStreamTimestamp?` | :323 |
| all remaining numerics | `int?` | :190 |

Common preamble in every comparator: **unknown value → `return !condition.IsRequired`**
(`:192-196`, `:235-239`, `:258-262`, `:282-286`, `:325-329`, `:346-350`). "Unknown" means
null, or empty string for `string?`, or `VideoRangeType.Unknown` for the range comparator
(`:346`).

**`int?`** (`:190-231`):
- `EqualsAny`: split `condition.Value` on `|`; each segment parsed with
  `int.TryParse(NumberStyles.Integer, InvariantCulture)`; any equal → `true`; else `false` (`:199-211`).
- Otherwise parse `condition.Value` as an int; on failure **return `false`** (`:230`).
- `Equals` → `==`; `GreaterThanEqual` → `>=`; `LessThanEqual` → `<=`; `NotEquals` → `!=`;
  anything else → `throw InvalidOperationException` (`:217-227`).

**`double?`** (`:280-321`): identical shape with
`double.TryParse(NumberStyles.Float | AllowThousands, InvariantCulture)` and the same four
operators plus throw (`:303-318`). Parse failure → `false` (`:320`).

**`string?`** (`:233-254`): `EqualsAny` → `Split('|').Contains(currentValue, OrdinalIgnoreCase)`;
`Equals` → ordinal-ignore-case equality; `NotEquals` → its negation; **`LessThanEqual` and
`GreaterThanEqual` throw `InvalidOperationException`** (`:251-253`).

**`bool?`** (`:256-278`): `bool.TryParse(condition.Value)` — accepts `"true"`/`"false"`
case-insensitively with surrounding whitespace, nothing else; parse failure → `false` (`:277`).
Only `Equals` and `NotEquals`; everything else throws (`:272`). **No `EqualsAny`.**

**`TransportStreamTimestamp?`** (`:323-342`): `Enum.Parse<TransportStreamTimestamp>(condition.Value, ignoreCase: true)`
— **unparseable value throws `ArgumentException`**, it does not return false (`:331`). Only
`Equals`/`NotEquals`; else throws (`:339`).

**`VideoRangeType?`** (`:344-387`):
1. Unknown or `VideoRangeType.Unknown` → `!IsRequired` (`:346-350`).
2. **Special case**: if the actual value is `HDR10Plus`, first evaluate the same condition against
   `HDR10`; if that returns `true`, return `true` (`:352-359`). Recursive call, one level.
3. `EqualsAny`: split on `|`, `Enum.TryParse(ignoreCase: true)` each, any equal → `true` (`:362-374`).
4. Else `Enum.TryParse(condition.Value, ignoreCase: true)`; `Equals`/`NotEquals` only, else throw
   (`:376-384`); parse failure → `false` (`:386`).

The HDR10Plus fallthrough happens *before* the operator dispatch and applies to **every**
operator, not just `Equals`. Worked example for `NotEquals HDR10` against an HDR10Plus source:
the recursive call evaluates the condition with `currentValue = HDR10`, giving `HDR10 != HDR10`
= `false`; the recursion does not short-circuit, so the normal path runs and returns
`HDR10Plus != HDR10` = `true`. Transliterate the recursion literally rather than reasoning about
which operators it can affect.

### 5.3 Composition

- **Conjunction within a profile.** `AggregateFailureConditions` (`:1421-1429`) folds `|` over
  the reasons of *all* failing conditions. A profile is satisfied iff its failing-condition set is
  empty, so all conditions must hold. `ApplyConditions` are also conjunctive — `.All(...)` at
  `:1071`, `:1102`, `:1712`, `:1730`, and `!....Any()` at `:2420`.
- **Disjunction across `DirectPlayProfiles`.** The `Select` at `:1330` evaluates every profile;
  the sort at `:1395-1397` then picks the best. A single profile with `failureReasons == 0` is
  enough for direct play.
- **Disjunction across `CodecProfiles` is not how they work** — every matching codec profile
  contributes its failures via `SelectMany` (`:2421`, `:1713`, `:1731`), so codec profiles are
  conjunctive across profiles as well as within.

### 5.4 Float widening — required

`videoFramerate` is a `float` in `StreamBuilder` (`:1051`, `:2358`) and a `float?` parameter in
`ConditionProcessor` (`:47`), but the only matching comparator takes `double?` (`:280`). C#
implicitly widens. `23.976f` widens to `23.975999832153320…`, while `double.TryParse("23.976")`
yields `23.976`. An `Equals` condition on framerate therefore essentially never matches, and
`LessThanEqual`/`GreaterThanEqual` are off by the widening error at the boundary.

The Go port must store the framerate as `float32`, convert to `float64` for the comparison, and
parse the condition value directly as `float64`. Parsing both sides as `float64` from the start
diverges.

---

## 6. `ApplyTranscodingConditions` (`:1741`)

Signature: `(StreamInfo item, IEnumerable<ProfileCondition> conditions, string? qualifier, bool enableQualifiedConditions, bool enableNonQualifiedConditions)`.

Every call site passes `enableQualifiedConditions = true, enableNonQualifiedConditions = true`
(`:192`, `:818`, `:1080`, `:1112`). The flags are dead in practice but must still be implemented
as written — they gate individual arms, not the loop.

### 6.1 Loop preamble — the dead-code skip

```
foreach condition in conditions:                                  // :1743
    value = condition.Value                                       // :1745
    if string.IsNullOrEmpty(value): continue                      // :1747-1750
    // No way to express this
    if condition.Condition == ProfileConditionType.GreaterThanEqual: continue   // :1752-1756
    switch condition.Property: ...
```

### 🔴 6.2 DEAD CODE THAT MUST BE PRESERVED

**`:1753` skips the entire loop body for every `GreaterThanEqual` condition.** Ten case arms
nevertheless contain `else if (condition.Condition == ProfileConditionType.GreaterThanEqual)`
branches. **All ten are unreachable:**

| Arm | Unreachable branch | Effect if it *were* reachable |
|:--|--:|:--|
| `AudioBitrate` | :1777-1780 | `AudioBitrate = max(num, AudioBitrate ?? num)` |
| `AudioSampleRate` | :1803-1806 | `AudioSampleRate = max(...)` |
| `AudioChannels` | :1839-1842 | `SetOption(qualifier,"audiochannels", max(...))` |
| `RefFrames` | :1964-1967 | `SetOption(qualifier,"maxrefframes", max(...))` |
| `VideoBitDepth` | :2000-2003 | `SetOption(qualifier,"videobitdepth", max(...))` |
| `Height` | :2158-2161 | `MaxHeight = max(...)` |
| `VideoBitrate` | :2184-2187 | `VideoBitrate = max(...)` |
| `VideoFramerate` | :2210-2213 | `MaxFramerate = max(...)` |
| `VideoLevel` | :2236-2239 | `SetOption(qualifier,"level", max(...))` |
| `Width` | :2262-2265 | `MaxWidth = max(...)` |

A port that "fixes" this by honouring `GreaterThanEqual` will raise clamps upward — larger
`MaxWidth`/`MaxHeight`, higher `VideoBitrate`, more `audiochannels` — everywhere a client profile
uses that operator, and will emit different transcode URLs than the C# server for the same
request. **Transliterate the skip at `:1753` and keep the ten branches as unreachable code**, so
that the port's structure still matches the oracle if the skip is ever removed upstream.

Recommended: implement them, mark them unreachable, and add an assertion that they are never
entered. The harness should have a corpus case with a `GreaterThanEqual` condition on `Width`
that fails if the port honours it.

### 6.3 Qualified / non-qualified gating

Three shapes appear across the arms:

- **Non-qualified only** — `if (!enableNonQualifiedConditions) continue;` at the top:
  `AudioBitrate` (:1762), `AudioSampleRate` (:1788), `IsAvc` (:1850), `IsAnamorphic` (:1872),
  `Height` (:2143), `VideoBitrate` (:2169), `VideoFramerate` (:2195), `Width` (:2247).
- **Either, chosen by qualifier** — `if (qualifier is empty) { if (!enableNonQualified) continue; } else { if (!enableQualified) continue; }`:
  `AudioChannels` (:1814-1827), `IsInterlaced` (:1894-1907), `RefFrames` (:1939-1952),
  `VideoBitDepth` (:1975-1988).
- **Qualified only** — `if (qualifier is empty) continue;`: `VideoProfile` (:2011-2014),
  `VideoRangeType` (:2043-2046), `VideoCodecTag` (:2079-2082), `VideoRotation` (:2111-2114),
  `VideoLevel` (:2221-2224).

`continue` inside the `switch` continues the **`foreach`**, not the switch. In Go, a bare
`continue` inside a `switch` inside a `for` behaves the same — but a Go `break` inside a `switch`
breaks the switch, matching C#'s `break` at the end of each arm. Both map cleanly; just do not
convert `continue` into `break`.

### 6.4 The 25 case labels

`ProfileConditionValue` has 26 members; 25 appear as case labels. **`AudioBitDepth` (23) has no
arm** and falls to `default: break` (`:2271-2272`).

| # | Property | Line | `Equals` | `LessThanEqual` | `GreaterThanEqual` |
|--:|:--|--:|:--|:--|:--|
| 1 | `AudioBitrate` | :1760 | `AudioBitrate = num` | `= min(num, AudioBitrate ?? num)` | *dead* |
| 2 | `AudioSampleRate` | :1786 | `AudioSampleRate = num` | `= min(num, AudioSampleRate ?? num)` | *dead* |
| 3 | `AudioChannels` | :1812 | `SetOption(q,"audiochannels",num)` | `= min(num, GetTargetAudioChannels(q) ?? num)` | *dead* |
| 4 | `IsAvc` | :1848 | `isAvc==true` → `RequireAvc = true` | — | — |
| 5 | `IsAnamorphic` | :1870 | `isAnamorphic==true` → `RequireNonAnamorphic = true` | — | — |
| 6 | `IsInterlaced` | :1892 | `isInterlaced==false` → `SetOption(q,"deinterlace","true")` | — | — |
| 7 | `AudioProfile` | :1924 | no-op | no-op | no-op |
| 8 | `Has64BitOffsets` | :1925 | no-op | no-op | no-op |
| 9 | `PacketLength` | :1926 | no-op | no-op | no-op |
| 10 | `NumStreams` | :1927 | no-op | no-op | no-op |
| 11 | `NumAudioStreams` | :1928 | no-op | no-op | no-op |
| 12 | `NumVideoStreams` | :1929 | no-op | no-op | no-op |
| 13 | `IsSecondaryAudio` | :1930 | no-op | no-op | no-op |
| 14 | `VideoTimestamp` | :1931 | no-op | no-op | no-op |
| 15 | `RefFrames` | :1937 | `SetOption(q,"maxrefframes",num)` | `= min(num, GetTargetRefFrames(q) ?? num)` | *dead* |
| 16 | `VideoBitDepth` | :1973 | `SetOption(q,"videobitdepth",num)` | `= min(num, GetTargetVideoBitDepth(q) ?? num)` | *dead* |
| 17 | `VideoProfile` | :2009 | `SetOption(q,"profile", join(',',split(value,'|')))` | — | — |
| 18 | `VideoRangeType` | :2041 | `SetOption(q,"rangetype", join(','))` | — | — |
| 19 | `VideoCodecTag` | :2077 | `SetOption(q,"codectag", join(','))` | — | — |
| 20 | `VideoRotation` | :2109 | `SetOption(q,"rotation", join(','))` | — | — |
| 21 | `Height` | :2141 | `MaxHeight = num` | `= min(num, MaxHeight ?? num)` | *dead* |
| 22 | `VideoBitrate` | :2167 | `VideoBitrate = num` | `= min(num, VideoBitrate ?? num)` | *dead* |
| 23 | `VideoFramerate` | :2193 | `MaxFramerate = num` | `= min(num, MaxFramerate ?? num)` | *dead* |
| 24 | `VideoLevel` | :2219 | `SetOption(q,"level",num)` | `= min(num, GetTargetVideoLevel(q) ?? num)` | *dead* |
| 25 | `Width` | :2245 | `MaxWidth = num` | `= min(num, MaxWidth ?? num)` | *dead* |
| — | *default* | :2271 | no-op (catches `AudioBitDepth`) | | |

Per-arm details that matter:

- **Arms 1-3, 15-16, 21-25** parse with `int.TryParse(value, InvariantCulture)` except
  `VideoFramerate`, which uses `float.TryParse(value, InvariantCulture)` (`:2200`). Parse failure
  → the arm does nothing (no `else`), then `break`.
- **Arm 4 `IsAvc`** (`:1855-1865`): `bool.TryParse(value)`; `RequireAvc = true` when
  (`isAvc == true` and `Equals`) or (`isAvc == false` and `NotEquals`). It is never set to
  `false`.
- **Arm 5 `IsAnamorphic`** (`:1877-1887`): same shape → `RequireNonAnamorphic = true`.
- **Arm 6 `IsInterlaced`** (`:1909-1919`): `SetOption(qualifier, "deinterlace", "true")` when
  (`isInterlaced == false` and `Equals`) or (`isInterlaced == true` and `NotEquals`). Note the
  inverted polarity relative to arms 4-5.
- **Arm 17 `VideoProfile`** (`:2018-2036`): `values = value.Split('|', RemoveEmptyEntries)` —
  **no `TrimEntries`**, unlike arms 18-20. `Equals` → `SetOption(q,"profile", string.Join(',', values))`.
  `EqualsAny` → if the current option value is non-empty and **ordinally equal** (`value == currentValue`,
  `:2028` — case-**sensitive**, unlike arms 18-20) to one of the values, keep it; else join all.
- **Arm 18 `VideoRangeType`** (`:2050-2072`): `Split('|', RemoveEmptyEntries | TrimEntries)`.
  `Equals` → join. `NotEquals` → `SetOption(q,"rangetype", string.Join(',', Enum.GetNames<VideoRangeType>().Except(values)))`
  — the complement over the **enum member names**, `Except` using default (ordinal, case-sensitive)
  equality and preserving `Enum.GetNames` declaration order. `EqualsAny` → keep-current-if-present
  using `string.Equals(..., OrdinalIgnoreCase)` (`:2064`).
- **Arms 19-20 `VideoCodecTag` / `VideoRotation`** (`:2086-2104`, `:2118-2136`): `Split('|',
  RemoveEmptyEntries | TrimEntries)`; `Equals` → join; `EqualsAny` → keep-current-if-present with
  `OrdinalIgnoreCase`. No `NotEquals` handling.
- **Arm 24 `VideoLevel`** parses with `int.TryParse` (`:2226`) even though
  `GetTargetVideoLevel` returns `double?` (`StreamInfo.cs:1326`). `Math.Min(int, double?)`
  promotes to `double`, and the result is written back via `.ToString(InvariantCulture)` — so a
  source level of `4.1` clamped against a condition value of `40` yields the string `"4.1"`, and
  the port must format the double with invariant formatting, not truncate to int.

`SetOption` key spelling (`StreamInfo.cs:815-825`): `qualifier + "-" + name` when the qualifier is
non-empty, bare `name` otherwise. Getter (`:843-853`) tries the qualified key first, then the bare
key. These strings reach the client through `StreamInfo.ToUrl`.

---

## 7. Subtitle sub-decision

### 7.1 `GetSubtitleProfile` (`:1455`)

```
if CanConsiderEmbedSubtitle(subtitleStream, playMethod, transcodingSubProtocol, outputContainer):   // :1464
    # pass 1 — embedded, exact format
    foreach profile in subtitleProfiles:                                        // :1467
        if !profile.SupportsLanguage(subtitleStream.Language): continue         // :1469-1472
        if profile.Method != Embed: continue                                    // :1474-1477
        if !ContainsContainer(profile.Container, outputContainer): continue      // :1479-1482
        if playMethod == Transcode && !IsSubtitleEmbedSupported(outputContainer): continue   // :1484-1487
        if subtitleStream.IsTextSubtitleStream == MediaStream.IsTextFormat(profile.Format)
           && profile.Format == subtitleStream.Codec (ordinal-ignore-case):
              return profile                                                    // :1489-1492
    # pass 2 — embedded, convertible format (same four guards)
    foreach profile in subtitleProfiles:                                        // :1496-1522
        ...
        if subtitleStream.IsTextSubtitleStream && subtitleStream.SupportsSubtitleConversionTo(profile.Format):
              return profile                                                    // :1518-1521
return GetExternalSubtitleProfile(..., allowConversion: false)                  // :1526
    ?? GetExternalSubtitleProfile(..., allowConversion: true)                   // :1527
    ?? new SubtitleProfile { Method = Encode, Format = subtitleStream.Codec }   // :1528-1532
```

The final fallback is **`Encode`** — burn-in — with the *source* codec as `Format`. This is what
vetoes direct play at `:1315-1317`.

`CanConsiderEmbedSubtitle` (`:1553-1564`):
```
if subtitleStream.IsExternal:
    return playMethod == Transcode && transcodingSubProtocol != hls && IsSubtitleEmbedSupported(outputContainer)
return playMethod != Transcode || transcodingSubProtocol != hls
```

`IsSubtitleEmbedSupported(transcodingContainer)` (`:1535-1551`):
```
if transcodingContainer is non-empty:
    if ContainsContainer(transcodingContainer, "ts,mpegts,mp4"): return false
    if ContainsContainer(transcodingContainer, "mkv,matroska"):  return true
return false
```
Argument order matters: `transcodingContainer` is the *profile list* and the literal is the
*input*. So a container of `"-mp4"` would be treated as a negative list. And an empty container
returns `false` (embed not supported).

`GetExternalSubtitleProfile(mediaSource, subtitleStream, subtitleProfiles, playMethod, transcoderSupport, allowConversion)`
(`:1566-1624`), first match wins in profile order:
```
if profile.Method != External && profile.Method != Hls: continue                          // :1570-1573
if profile.Method == Hls && playMethod != Transcode: continue                             // :1575-1578
if !profile.SupportsLanguage(subtitleStream.Language): continue                           // :1580-1583
if !subtitleStream.IsExternal && playMethod == Transcode
   && !transcoderSupport.CanExtractSubtitles(subtitleStream.Codec): continue              // :1585-1588
isVobSubMksProfile = IsVobSubMksProfile(profile, subtitleStream)                          // :1590
if (profile.Method == External && (isVobSubMksProfile
        || (!IsVobSubMksDeliveryProfile(profile)
            && subtitleStream.IsTextSubtitleStream == MediaStream.IsTextFormat(profile.Format))))
   || (profile.Method == Hls && subtitleStream.IsTextSubtitleStream):                     // :1592-1595
    requiresConversion = !isVobSubMksProfile
                         && profile.Format != subtitleStream.Codec (ordinal-ignore-case)  // :1597-1598
    if !requiresConversion: return profile                                                // :1600-1603
    if !allowConversion:    continue                                                      // :1605-1608
    if mediaSource.IsInfiniteStream: continue                                             // :1611-1614
    if subtitleStream.IsTextSubtitleStream && subtitleStream.SupportsExternalStream
       && subtitleStream.SupportsSubtitleConversionTo(profile.Format): return profile     // :1616-1619
return null
```

`IsVobSubMksDeliveryProfile(profile)` (`:1626-1631`): `MediaStream.IsVobSubFormat(profile.Format)`
and `profile.Container` non-whitespace and `ContainsContainer(profile.Container, "mks")`.

`IsVobSubMksProfile(profile, subtitleStream)` (`:1633-1639`): the above, **and**
`subtitleStream.IsVobSubSubtitleStream`, **and** (`!subtitleStream.IsExternal` or its `Path` ends
with `".mks"` ordinal-ignore-case). Rationale in the comment at `:1635`: FFmpeg cannot mux VobSub
back into an `.idx`/`.sub` pair.

`SupportsLanguage` (`SubtitleProfile.cs:48-61`): empty `Language` → `true`; empty stream language
is replaced with `"und"`; then `ContainsContainer(Language, subLanguage)`.

### 7.2 Feedback into direct play

Three call sites, three different argument sets:

| Call site | `playMethod` | `outputContainer` | `transcodingSubProtocol` | Result used for |
|:--|:--|:--|:--|:--|
| `:1313` | `DirectPlay` (literal) | source `container` | `null` | `subtitleProfileReasons` → veto |
| `:775` | actual `directPlay.Value` | `directPlayProfile?.Container` | `null` | `SubtitleDeliveryMethod`, `SubtitleFormat` |
| `:810` | `Transcode` (literal) | `transcodingProfile.Container` | `transcodingProfile.Protocol` | + `SubtitleCodecs` |

The veto (`:1315-1321`): `Method` not in {`Drop`, `External`, `Embed`} → `SubtitleCodecNotSupported`.
Since the enum has exactly five members, this means **`Encode` or `Hls`**. `Hls` can only be
returned when `playMethod == Transcode` (`:1575-1577`), and `:1313` passes `DirectPlay`, so in
practice the veto fires on `Encode` — the fallback at `:1528-1532`. But transliterate the
three-way exclusion, not the simplification.

`SubtitleCodecNotSupported` (bit 3) is **not** in `DirectStreamReasons`, so a subtitle veto blocks
direct stream as well as direct play.

---

## 8. Other must-preserve quirks

### 8.1 DVD/BluRay folders (`:715-719`)

```
if item.VideoType == VideoType.Dvd || item.VideoType == VideoType.BluRay:
    isEligibleForDirectPlay = false
```
Unconditional, no reason bit is set, and it happens after `ForceDirectPlay` was folded into
`isEligibleForDirectPlay` at `:711`. Direct **stream** remains eligible. Because no
`TranscodeReason` is recorded, the response can report a `Transcode`/`DirectStream` play method
with a reason set that never mentions the folder type.

### 8.2 `containerSupported` mutated inside the LINQ `Select` (`:1324`, `:1342`, `:1411`)

`containerSupported` is declared at `:1324`, captured by the `Select` lambda, and assigned `true`
at `:1342` for every profile whose container matches. It is **read** at `:1411`, inside the
`Where` of the fallback query.

The ordering dependency: LINQ `Select` is lazy. The value at `:1411` is only correct because
`.ToArray()` at `:1398` forces full enumeration of the `Select` before `.ToLookup()` at `:1399`,
and both run before `:1411`. Remove the `.ToArray()` and the flag would be read mid-enumeration.

Additional subtlety for the port: `:1411` is inside a `Where` over `analyzedProfiles[false]`,
which is a *materialized* lookup, so the `Where` runs after enumeration is complete regardless.
Both mechanisms currently agree. In Go the natural translation is a plain loop that sets
`containerSupported` while building the analysis slice, then a second pass for the fallback —
which reproduces the observed behaviour. **Do not** compute `containerSupported` from only the
profiles examined before the winner; it reflects **all** video direct-play profiles.

### 8.3 Input mutation

`StreamBuilder` writes into the caller's `MediaSourceInfo` and its `MediaStream`s. These objects
are serialized back to the client in the same `PlaybackInfo` response, so the mutations are on the
wire.

| Line | Mutation |
|--:|:--|
| :157 | `item.TranscodingContainer = remuxContainer` (audio direct stream) |
| :597-598 | `item.TranscodingContainer` / `TranscodingSubProtocol` from the transcoding profile |
| :636-637 | `item.TranscodingContainer` / `TranscodingSubProtocol` from the direct-play profile |
| :833 | `item.Container = Normalize...(...)` at the end of `BuildVideoItem` |
| :1018 | `playlistItem.TargetAudioStream.Channels = TranscodingMaxAudioChannels` |

A Go port that takes `MediaSourceInfo` by value, or deep-copies defensively, will produce a
different response body even with an identical `StreamInfo`.

### 8.4 `ToDictionary` on stream identity (`:1308`)

`candidateAudioStreams.ToDictionary(s => s, ...)` keys on reference identity. In Go, key by the
slice index or by a pointer, **not** by a struct value — two audio streams with identical field
values are distinct keys in C# and must remain distinct.

### 8.5 `GetRank`'s `ref` parameter (`:2325`)

`private int GetRank(ref TranscodeReason a, TranscodeReason[] rankings)` never writes `a`. The
`ref` is vestigial. Port by value.

### 8.6 Log-only divergences

`LogConditionFailure` (`:1431-1441`) passes `type` and `profile.Name` in the wrong positional
order relative to the format string (`{0}` gets `type`, but the message reads
`"Profile: {0}, DirectPlay=false. Reason={1}..."`). `GetCompatibilityContainer` passes the literal
`"VideoCodecProfile"` as its type string (`:2391`) even though it processes container profiles.
Neither affects the wire. Do not "fix" them into behaviour.

---

## 9. Needs a runtime experiment

Items that source reading cannot settle. Each needs a probe against a real 10.10-line server
before the harness corpus can claim coverage.

1. **Do real clients ever send `GreaterThanEqual` conditions?** If the corpus contains none, the
   dead branches in §6.2 are untestable and the protection is theoretical. If some do — the
   likely candidates are `VideoBitrate`/`Height` floors in third-party profiles — the skip is
   directly observable and must be pinned. Probe: enumerate `DeviceProfile` payloads from the
   Jellyfin web client, Findroid, Infuse, and the DLNA built-in profiles.
2. **Do any shipped or common profiles put a non-audio `ProfileConditionValue` inside a
   `CodecProfile` of `Type = Audio`/`VideoAudio`?** That throws (§5.1). Confirm the real server
   returns 500 rather than a handled error, so the port's error behaviour matches.
3. **`containerSupported` ordering (§8.2)** with a profile list where some entries match the
   container and others do not, *and* where the best-ranked failure comes from a
   container-mismatching profile. Confirm the reported `TranscodeReasons` matches the
   "suppress container reasons" reading of `:1411`.
4. **Audio `EnableDirectPlay = false` with an otherwise-matching profile** (§4.3 step 5, hazard
   H10). Confirm the real server returns `PlayMethod = Transcode` with `TranscodeReasons` empty.
5. **`:792` overwrite on the direct-stream path** (hazard H1). Confirm that a direct-stream result
   whose `BuildStreamVideoItem` would have added `AudioCodecNotSupported` reports it **absent** in
   the response.
6. **Float widening on `VideoFramerate`** (§5.4). A `LessThanEqual 23.976` condition against a
   23.976 fps source: does the real server treat it as satisfied? The widened `float32` is
   slightly *below* the parsed `float64`, so `<=` should hold and `>=` should fail — verify.
7. **`VideoRangeType NotEquals` complement string** (§6.4 arm 18). Capture the exact
   `Enum.GetNames<VideoRangeType>()` order from the running server; the Go port must emit the same
   comma-joined order.
8. `MediaStream.IsTextFormat`, `IsVobSubFormat`, `SupportsSubtitleConversionTo`,
   `SupportsExternalStream`, and `ITranscoderSupport.CanExtractSubtitles` /
   `CanEncodeToAudioCodec` are consulted throughout §7 and §4.6 but are **[NOT IN SOURCE]** for
   this document — they live outside `StreamBuilder.cs`/`ConditionProcessor.cs` and need their own
   transliteration pass before the subtitle gates can be verified.

---

## 10. PORT HAZARDS

Every entry is a place where a clean, correct-looking Go implementation produces a different
`StreamInfo` or `TranscodeReasons` than the C#. Each needs a corpus case that **fails when the
hazard is "fixed"** (gate G6).

**H1 — `:792` destroys direct-stream reasons.**
`playlistItem.TranscodeReasons = transcodeReasons` is a plain assignment that runs *after*
`BuildStreamVideoItem` was called at `:770`. Every bit that `BuildStreamVideoItem` OR-ed in at
`:953`, `:1002`, `:1005`, and `:1017` is discarded on the direct-stream path. On the transcode
path the order is reversed (`:792` before `:804`) and the bits survive. A port that changes `=`
to `|=`, or that moves the assignment, adds reasons to direct-stream responses that Jellyfin does
not report.

**H2 — `:806` discards the `DirectStream` play method from `GetVideoTranscodeProfile`.**
`GetVideoTranscodeProfile` computes `playMethod = DirectStream` when `rank.Video == 1` (`:910-913`),
returns it, the caller tests `playMethod.HasValue` (`:800`) — and then unconditionally overwrites
with `PlayMethod.Transcode` (`:806`). The returned play method only ever functions as a non-null
sentinel, and since it is a non-nullable `PlayMethod` in the tuple it is *always* non-null,
including the `default` from `FirstOrDefault()` on an empty sequence (`:919`). A port that
propagates the `DirectStream` will report a play method Jellyfin never reports.

**H3 — `continue` vs `break` in the codec-profile inner loops.**
`:1081` (video) uses `continue`; `:1113` (audio) uses `break`. So a video codec profile's
conditions are applied **once per matching codec in `playlistItem.VideoCodecs`**, while an audio
codec profile's are applied **once, for the first matching codec only**. With a multi-codec
transcoding profile (`"h264,hevc"`), video conditions are applied twice with different qualifiers
and the second application's `SetOption` calls land under a different key. Symmetrising the two
loops changes the `StreamOptions` map.

**H4 — `containerSupported` and enumeration order.**
See §8.2. The flag reflects **all** video direct-play profiles because `.ToArray()` at `:1398`
forces full enumeration before it is read at `:1411`. A port that streams/short-circuits the
profile analysis and reads the flag early will report `ContainerNotSupported` where Jellyfin
suppresses it.

**H5 — codec-reason masking direction (`:1369-1377`).**
Fine-grained codec reasons are added **only when** the coarse `…CodecNotSupported` bit is
**clear**. The intuitive reading — "add all reasons we found" — inverts this and produces strictly
larger reason sets. Note the test is against the running `failureReasons`, which already includes
container and subtitle bits.

**H6 — `DirectStreamReasons` subtraction (`:1379`).**
`directStreamFailureReasons = failureReasons & ~DirectStreamReasons`. Getting the alias contents
wrong (§1.2) silently reclassifies direct play as direct stream or vice versa. The two easiest
mistakes: putting `VideoCodecTagNotSupported` into `VideoCodecReasons` (it is not), and adding
`ContainerBitrateExceedsLimit` to `DirectStreamReasons` (it is not).

**H7 — DVD/BluRay clears direct play only, and sets no reason (`:715-719`).**
Also: `ForceDirectPlay` does **not** rescue it at `:711`, but `GetVideoDirectPlayProfile` returns
`DirectPlay` unconditionally at `:1288-1291` whenever `ForceDirectPlay` is set — and that function
is still reached because `:734` also tests `isEligibleForDirectStream`. So `ForceDirectPlay` on a
BD folder *does* yield `DirectPlay`, via a different route. A port that puts the folder check
inside `GetVideoDirectPlayProfile`, or that returns early when `isEligibleForDirectPlay` is false,
diverges.

**H8 — `GetRank` polarity and the descending sort.**
Lower rank = more severe. The sort is `ThenByDescending(Rank)` (`:1396`). Inverting either
convention picks a different profile and therefore a different `TranscodeReasons` and
`AudioStreamIndex`. `GetRank` returns `len(rankings)+1 = 6` when nothing matches.

**H9 — profile order is client-supplied and is the final tiebreak (`:1330`, `:1397`).**
`order` is the index within the `Type == Video` filtered sequence. Sorting into a map, using a
set, or re-ordering profiles for efficiency changes which profile wins among equals — and hence
the `Profile`, `AudioStreamIndex`, and reason set returned.

**H10 — audio direct play with `EnableDirectPlay = false` yields a reason-less transcode.**
`GetAudioDirectPlayProfile` `:467-473`: when a profile matched and `transcodeReasons == 0` but
`options.EnableDirectPlay` is false, the direct-stream gate's exact-equality test at `:490` fails
(`0 != ContainerNotSupported`), and the function returns `(profile, null, 0)`. The response is
`PlayMethod = Transcode` with an **empty** `TranscodeReasons`. Any port that "helpfully" adds a
reason here diverges.

**H11 — `GetTranscodeReasonsFromDirectPlayProfile` emits `VideoCodecNotSupported` for audio.**
`:508-544`: `videoSupported` and `audioSupported` initialise to `false` and are only assigned
inside the container-match branch. For an **audio** item whose container matches no profile, the
result is `ContainerNotSupported | VideoCodecNotSupported | AudioCodecNotSupported` — a video bit
on a pure-audio response. Also: the two flags are **assigned, not accumulated**, so their final
values come from the last container-matching profile, not a union.

**H12 — six `ProfileConditionValue`s map to reason `0` (`:322`, `:332`, `:345`, `:349`, `:353`, `:387`).**
`Has64BitOffsets`, `IsAvc`, `NumAudioStreams`, `NumVideoStreams`, `PacketLength`, `VideoTimestamp`
produce no bit when they fail. Since `failureReasons |= 0` is a no-op, a failing condition on any
of these **does not block direct play**. Inventing a reason bit for them changes the play method.
`Width` and `Height` both map to `VideoResolutionNotSupported` — do not split them.

**H13 — unhandled conditions are permissive only in `IsVideoConditionSatisfied`.**
The other three entry points **throw** (`ConditionProcessor.cs:121`, `:147`, `:186`). §5.1. A port
that returns `true` everywhere turns a 500 into a successful-but-different response.

**H14 — comparator operator support is not uniform, and unsupported operators throw.**
`string?` has no `LessThanEqual`/`GreaterThanEqual` (`ConditionProcessor.cs:251-253`);
`bool?` and `TransportStreamTimestamp?` have neither those nor `EqualsAny` (`:272`, `:339`);
`TransportStreamTimestamp` throws on an unparseable **value** (`:331`) where every other
comparator returns `false`. Reproduce each throw.

**H15 — unknown value → `!IsRequired`, and `IsRequired` defaults to `true`.**
`ConditionProcessor.cs:192-196` et al.; `ProfileCondition.cs:12` vs `:16-17`. A port that defaults
`IsRequired` to `false` (the Go zero value) inverts the treatment of every condition whose actual
value is unknown.

**H16 — `float32` → `float64` widening on `VideoFramerate`.** §5.4. Store as `float32`, widen at
comparison time, parse the condition value as `float64`.

**H17 — the `GreaterThanEqual` whole-loop skip (`:1753`) and its ten unreachable branches.** §6.2.
The single most likely "cleanup" to break the port.

**H18 — `AudioBitDepth` has no arm in `ApplyTranscodingConditions`.** 25 case labels for 26 enum
members; `AudioBitDepth` falls through to `default` (`:2271`). It *is* handled in the compatibility
checks (`ConditionProcessor.cs:144`, `:183`) and does map to a reason bit (`:363`) — so it can
block direct play but can never clamp a transcode.

**H19 — mixed case sensitivity.** Container/codec matching is ordinal-**ignore**-case
(`ContainerHelper.cs:98`). But `_supportedHlsAudioCodecs*.Contains(...)` at `:138`/`:142` and
`_supportedHlsVideoCodecs.Contains(...)` at `:947` use `List<string>.Contains`, which is
ordinal **case-sensitive**. And `ApplyTranscodingConditions` arm 17 (`VideoProfile`, `:2028`) uses
`==` (case-sensitive) for its `EqualsAny` keep-current test while arms 18-20 use
`OrdinalIgnoreCase`. Transliterate each comparison individually.

**H20 — input mutation is observable on the wire.** §8.3. `MediaSourceInfo.Container`,
`TranscodingContainer`, `TranscodingSubProtocol`, and `MediaStream.Channels` are written by the
builder and serialized in the same response.

**H21 — `:1031` stores audio channels under the *video* codec qualifier.**
`qualifier` is `videoStream?.Codec` from `:958` and is never reassigned before `:1031`, so the
key is e.g. `"h264-audiochannels"`. `GetTargetAudioChannels(qualifier)` in
`ApplyTranscodingConditions` arm 3 is then called with whatever qualifier that arm received —
which for audio codec profiles is the *audio* codec (`:1112`) — so the two do not line up. Both
sides must be transliterated as written.

**H22 — `SetStreamInfoOptionsFromDirectPlayProfile` dereferences `item.VideoStream` unguarded
(`:642`).** `playlistItem.VideoCodecs = [item.VideoStream.Codec]`. Every other read of the video
stream in this file is null-conditional. A video media source with no video stream that reaches
direct stream throws `NullReferenceException` → 500. Reproduce the failure, do not add a guard.

**H23 — `FirstOrDefault()` on value-tuple sequences returns a zero tuple, not null.**
`:919` (`GetVideoTranscodeProfile`) and `:1403`/`:1412` (`GetVideoDirectPlayProfile`). At `:919`
the zero tuple has `PlayMethod = Transcode` (0), which is why `playMethod.HasValue` is always
true; at `:1412` it has `TranscodeReason = 0`, which is what triggers the `DirectPlayError`
substitution at `:1413-1416`. In Go these must be explicit zero values, not `nil` checks.

**H24 — `ContainerHelper` empty-string semantics.** Empty *profile* list → `true` (supports
everything, `ContainerHelper.cs:84-88`); empty *input* → `isNegativeList`
(`:65-68`). Leading `-` on the profile list negates (`:24-28`), but only through the two-argument
overloads — `CodecProfile.ContainsAnyCodec` passes `isNegativeList: false` explicitly for the
codec side (`CodecProfile.cs:67`, `:92`), so a `-` prefix in `CodecProfile.Codec` is **not**
negation. Getting either default backwards flips direct-play eligibility wholesale.

The two rules are **checked in a fixed order** and the order is observable: the empty-*input*
check (`:65-68`) precedes the empty-*profile* check (`:84-88`) on the `string?` path. A null codec
against an empty profile therefore returns `false`, not `true` — which is why a media source with
no video stream fails `SupportsVideoCodec` against every direct-play profile (§3.4). A port that
evaluates "empty profile matches everything" first inverts this.

**H25 — `.Reverse()` on codec profiles (`:1073`, `:1104`).** Profiles are applied last-to-first so
that the **first** profile in client order wins the final `SetOption`. Dropping the reverse, or
reversing the wrong collection, silently changes every clamped value when two codec profiles
overlap.
