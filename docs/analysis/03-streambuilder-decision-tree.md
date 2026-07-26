# StreamBuilder decision tree

`MediaBrowser.Model/Dlna/StreamBuilder.cs`, 2,479 lines. This is the function that decides
direct play vs direct stream vs transcode. Everything in `POST /Items/{itemId}/PlaybackInfo`
that matters flows through here.

**Transliterate this file. Do not redesign it.** The ordering of the checks, the ranking of
failure reasons, and at least one block of dead code are all load-bearing for wire
compatibility.

## Inputs

The client supplies a `DeviceProfile` with five arrays. They are not interchangeable and they
are consulted at different points:

| Array | Consulted by | Effect |
|:--|:--|:--|
| `DirectPlayProfiles` | `GetVideoDirectPlayProfile` (`:1326`) | Candidate list. Each entry gates container + video codec + audio codec. Iterated **in client-supplied order**, and order survives into the tiebreak (`:1394`). |
| `ContainerProfiles` | `GetCompatibilityContainer` (`:2384`) | Conditions evaluated against the source container. |
| `CodecProfiles` | `GetCompatibilityVideoCodec` (`:2407`), `GetCompatibilityAudioCodec` (`:2437`), `GetCompatibilityAudioCodecDirect` (`:2467`) | Conditions evaluated per codec. Produce `TranscodeReason` bits. |
| `TranscodingProfiles` | `GetVideoTranscodeProfile` (`:837`) | Only consulted **after** direct play/stream has already failed. Chooses output container, protocol (`http`/`hls`), codecs. |
| `SubtitleProfiles` | `GetSubtitleProfile` (`:1455`) | Chooses delivery method per subtitle stream. Can independently veto direct play. |

## Control flow — video

`BuildVideoItem` (`:646`):

1. Pick subtitle stream: explicit `options.SubtitleStreamIndex`, else `GetDefaultSubtitleStreamIndex` (`:549`).
2. Pick audio stream and build a **candidate set** (`:670-707`). The candidate set is narrowed by
   `item.DefaultAudioIndexSource` flags (`User` / `Language` / `Default`). If the user pinned an
   index, the set is exactly one stream and no reselection happens.
3. `IsBitrateLimitExceeded` (`:1641`) → sets `isEligibleForDirectPlay` / `isEligibleForDirectStream` (`:711-713`).
   Overridable by `options.ForceDirectPlay` / `ForceDirectStream`.
4. **DVD/BluRay folders are unconditionally ineligible for direct play** (`:717-720`). Easy to miss.
5. If either eligibility holds → `GetVideoDirectPlayProfile` (`:1278`).
6. If the result is neither DirectPlay nor DirectStream → `GetVideoTranscodeProfile` (`:837`),
   then `ApplyTranscodingConditions` (`:816`) but **only if** the accumulated reasons intersect
   `VideoReasons | ContainerBitrateExceedsLimit`.

### GetVideoDirectPlayProfile — the core

`:1278`. Short-circuits on `ForceDirectPlay` / `ForceDirectStream` before evaluating anything (`:1288-1296`).

Then it computes three reason sets **once**, outside the profile loop:

- `containerProfileReasons` from `ContainerProfiles`
- `videoCodecProfileReasons` from `CodecProfiles`
- `audioStreamMatches` — a dict of candidate audio stream → reasons

and a fourth, `subtitleProfileReasons`, which is set to `SubtitleCodecNotSupported` if the chosen
subtitle profile's method is anything other than `Drop`, `External`, or `Embed` (`:1313-1322`).

For each `DirectPlayProfile` of type Video, in order (`:1327`):

```
directPlayProfileReasons = 0
if !SupportsContainer(container)      -> |= ContainerNotSupported
else                                  -> containerSupported = true     # note: set across iterations
if !SupportsVideoCodec(videoCodec)    -> |= VideoCodecNotSupported
selectedAudioStream = first candidate whose codec this profile supports
if none                               -> |= AudioCodecNotSupported
else                                  -> audioCodecProfileReasons = audioStreamMatches[selected]

failureReasons = directPlayProfileReasons | containerProfileReasons | subtitleProfileReasons
if VideoCodecNotSupported not set     -> failureReasons |= videoCodecProfileReasons
if AudioCodecNotSupported not set     -> failureReasons |= audioCodecProfileReasons

directStreamFailureReasons = failureReasons & ~DirectStreamReasons

if failureReasons == 0 && eligibleDP && mediaSource.SupportsDirectPlay      -> DirectPlay
elif directStreamFailureReasons == 0 && eligibleDS && SupportsDirectStream  -> DirectStream
else                                                                        -> null
```

The codec-profile reasons are **masked by** the codec-not-supported reasons. If the container
profile already rejected the video codec outright, the finer-grained codec conditions are not
added. Getting this backwards produces subtly different `TranscodeReasons` in the response.

Results are sorted `PlayMethod desc, Rank desc, Order asc` (`:1391-1394`) and the first with a
non-null `PlayMethod` wins. `GetRank` (`:2325`) scores against
`[VideoCodecNotSupported, VideoCodecReasons, AudioCodecNotSupported, AudioCodecReasons, ContainerReasons]` (`:1325`).

If nothing matched, the reported failure reason is taken from the first rejected profile,
filtered by `!containerSupported || !hasFlag(ContainerNotSupported)` (`:1403-1406`) — i.e. if *any*
profile matched the container, container-mismatch reasons are suppressed from the explanation.
Falls back to `DirectPlayError` if the set is empty (`:1407-1410`).

## ProfileCondition composition

`ProfileConditionType` — 5 operators (`MediaBrowser.Model/Dlna/ProfileConditionType.cs`):
`Equals`, `NotEquals`, `LessThanEqual`, `GreaterThanEqual`, `EqualsAny`.

`ProfileConditionValue` — 26 members (`MediaBrowser.Model/Dlna/ProfileConditionValue.cs`).
Note the enum skips 15; do not assume contiguity when porting.

Conditions compose by **conjunction within a profile** (`AggregateFailureConditions`, `:1421`,
folds with `|=` over the failing conditions) and **disjunction across DirectPlayProfiles** (first
profile with zero failures wins).

### Evaluation — `ConditionProcessor.cs` (389 lines)

Four entry points, each handling a disjoint subset:

| Entry point | Line | Values handled | Unhandled property |
|:--|--:|--:|:--|
| `IsVideoConditionSatisfied` | `:38` | 19 | returns `true` (`:100-101`) |
| `IsImageConditionSatisfied` | `:112` | 2 | **throws** `ArgumentException` (`:120-122`) |
| `IsAudioConditionSatisfied` | `:134` | 4 | **throws** `ArgumentException` (`:146-148`) |
| `IsVideoAudioConditionSatisfied` | `:162` | 6 | **throws** `ArgumentException` (`:185-187`) |

**Unhandled-property behaviour is not uniform.** Only the video entry point is permissive. The
other three throw, which surfaces as a 500 from `PlaybackInfo` — so a client `CodecProfile` of
`Type = Audio` or `VideoAudio` carrying, say, a `Width` condition crashes the audio compatibility
check. The port must reproduce the throw, not silently return `true`. See
`08-streambuilder-port.md` §5.1 and hazard H13.

`Has64BitOffsets` is handled by no entry point at all.

### Application — `ApplyTranscodingConditions` (`:1741`)

Once transcoding is chosen, conditions are replayed to *clamp* output parameters. 25 `case`
arms over `ProfileConditionValue`.

**Dead code that must be preserved.** `:1752-1755` skips the whole loop body for
`ProfileConditionType.GreaterThanEqual`:

```csharp
// No way to express this
if (condition.Condition == ProfileConditionType.GreaterThanEqual)
{
    continue;
}
```

Yet many case arms still contain `else if (condition.Condition == ProfileConditionType.GreaterThanEqual)`
branches (e.g. `:1776-1779` for `AudioBitrate`). Those branches are unreachable. A port that
"cleans this up" by honouring `GreaterThanEqual` will clamp bitrates upward where Jellyfin does
not, and will diverge on any profile that uses it. **Transliterate the skip.**

The `qualifier` / `enableQualifiedConditions` / `enableNonQualifiedConditions` triple controls
whether a condition applies to a specific codec or to the stream generally. Both flags are
checked per-arm, not centrally.

## Subtitle sub-decision

`GetSubtitleProfile` (`:1455`) returns a `SubtitleDeliveryMethod`:
`Encode` (burn in), `Embed`, `External`, `Hls`, `Drop`.

This is a genuine second decision tree, and it feeds back into the first: a subtitle that
resolves to `Encode` or `Hls` sets `SubtitleCodecNotSupported` and kills direct play (`:1316-1322`).
Helpers: `IsSubtitleEmbedSupported` (`:1535`), `CanConsiderEmbedSubtitle` (`:1553`),
`GetExternalSubtitleProfile` (`:1566`), plus two VobSub/MKS special cases (`:1626`, `:1633`).

## Outputs

`StreamInfo` carrying `PlayMethod` (`DirectPlay` / `DirectStream` / `Transcode`), `SubProtocol`
(`MediaStreamProtocol.http` | `hls`), `Container`, `VideoCodecs`, `AudioCodecs`,
`SubtitleDeliveryMethod`, `SubtitleFormat`, and the accumulated `TranscodeReasons` bitfield.

`TranscodeReason` (`MediaBrowser.Model/Session/TranscodeReason.cs`) is 28 flags, bits 0-27.
Group aliases at `StreamBuilder.cs:22-27`:

- `ContainerReasons` = ContainerNotSupported | ContainerBitrateExceedsLimit
- `AudioCodecReasons` = 7 audio-parameter bits
- `AudioReasons` = AudioCodecNotSupported | AudioCodecReasons
- `VideoCodecReasons` = 11 video-parameter bits
- `VideoReasons` = VideoCodecNotSupported | VideoCodecReasons
- `DirectStreamReasons` = AudioReasons | ContainerNotSupported | VideoCodecTagNotSupported

`DirectStreamReasons` is the definition of "things remuxing can fix". It is subtracted from the
failure set to test direct-stream eligibility (`:1379`). This one line is the whole difference
between direct play and direct stream.

## HLS codec allowlists

Hardcoded, not profile-driven (`:32-34`):

- video: `h264, hevc, vp9, av1`
- audio in TS: `aac, ac3, eac3, mp3`
- audio in MP4: `aac, ac3, eac3, mp3, alac, flac, opus, dts, truehd`

## Needs a runtime experiment

- `containerSupported` (`:1323`) is mutated inside a LINQ `Select` that is only forced by
  `.ToArray()` at `:1395`. Its value when read at `:1405` depends on full enumeration having
  completed. It does, here, but the ordering is fragile and worth confirming against the real
  server with a profile where some entries match the container and others do not.
- Whether real clients ever send `GreaterThanEqual` conditions in practice. If none do, the dead
  code is harmless either way; if some do, it is a required behaviour.
