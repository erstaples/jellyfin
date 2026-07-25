# EncodingHelper shape

`MediaBrowser.Controller/MediaEncoding/EncodingHelper.cs`, 7,987 lines. Conditional ffmpeg argv
construction. This file, not StreamBuilder, is the bulk of the port.

**Transliterate. Do not redesign.** These lines encode empirical knowledge about driver quirks
that cannot be derived from first principles.

## Acceleration types

`MediaBrowser.Model/Entities/HardwareAccelerationType.cs` — **8** members:

| Value | Name |
|--:|:--|
| 0 | `none` (software) |
| 1 | `amf` (AMD) |
| 2 | `qsv` (Intel Quick Sync) |
| 3 | `nvenc` (NVIDIA) |
| 4 | `v4l2m2m` (Video4Linux2) |
| 5 | `vaapi` |
| 6 | `videotoolbox` (macOS) |
| 7 | `rkmpp` (Rockchip) |

Dispatch on this enum happens in at least two places: `GetHwaccelType` (`:6587`, decode-side) and
the encoder selection block at `:6660-6733`. Decoder selection is a separate switch at `:6499`.

## True dimensionality: 16 filter-chain builders, not 8

Each returns `(MainFilters, SubFilters, OverlayFilters)` — a triple, because subtitle burn-in is a
second graph overlaid onto the main one.

Seven **dispatchers**:

| Method | Line |
|:--|--:|
| `GetSwVidFilterChain` | 3853 |
| `GetNvidiaVidFilterChain` | 3975 |
| `GetAmdVidFilterChain` | 4183 |
| `GetIntelVidFilterChain` | 4409 |
| `GetVaapiVidFilterChain` | 5017 |
| `GetAppleVidFilterChain` | 5756 |
| `GetRkmppVidFilterChain` | 5946 |

Nine **concrete pipelines** they dispatch to:

| Method | Line | Notes |
|:--|--:|:--|
| `GetNvidiaVidFiltersPrefered` | 4001 | |
| `GetAmdDx11VidFiltersPrefered` | 4211 | Windows D3D11 |
| `GetIntelQsvDx11VidFiltersPrefered` | 4455 | Windows D3D11 |
| `GetIntelQsvVaapiVidFiltersPrefered` | 4747 | Linux QSV-over-VAAPI |
| `GetIntelVaapiFullVidFiltersPrefered` | 5078 | |
| `GetAmdVaapiFullVidFiltersPrefered` | 5314 | |
| `GetVaapiLimitedVidFiltersPrefered` | 5549 | fallback when full VAAPI unavailable |
| `GetAppleVidFiltersPreferred` | 5785 | note the spelling differs from the others |
| `GetRkmppVidFiltersPrefered` | 5978 | |

So the port target is **10 argv-producing pipelines** (9 hardware + software), not 8. The
expansion comes from VAAPI splitting three ways (Intel-full / AMD-full / limited), QSV splitting
two ways (DX11 / VAAPI), and AMF splitting by platform.

## Cross-cutting concerns that multiply

Each of these is evaluated inside most of the 10 pipelines, with per-driver variations:

**Tonemapping** — the largest multiplier. Five separate availability predicates:

| Predicate | Line |
|:--|--:|
| `IsSwTonemapAvailable` | 346 |
| `IsHwTonemapAvailable` | 358 |
| `IsVulkanHwTonemapAvailable` | 393 |
| `IsIntelVppTonemapAvailable` | 406 |
| `IsVideoToolboxTonemapAvailable` | 430 |

plus `GetHwTonemapFilter` (`:3691`) and two mode families —
`_legacyTonemapModes = [max, rgb]`, `_advancedTonemapModes = [lum, itp]` (`:127-128`).

**Deinterlace** — `IsDeinterlaceAvailable` (`:448`), `GetSwDeinterlaceFilter` (`:3625`),
`GetHwDeinterlaceFilter` (`:3635`).

**Subtitle burn-in** — the `SubFilters` / `OverlayFilters` legs of every chain triple.

**Scaling / format conversion** — `GetVideoProcessingFilterParam` (`:6231`),
`GetOverwriteColorPropertiesParam` (`:6346`).

## Driver-quirk predicates — the part that cannot be derived

`IMediaEncoder` exposes runtime-probed driver facts that gate argv construction:

- `IsVaapiDeviceInteliHD`, `IsVaapiDeviceInteli965`, `IsVaapiDeviceAmd`
- `IsVaapiDeviceSupportVulkanDrmInterop`, `IsVaapiDeviceSupportVulkanDrmModifier`

Referenced throughout, e.g. `:1046`, `:1050`, `:1061`, `:1069`, `:1075`, `:1706`, `:1784`, `:2070`,
`:2347`, `:5058`, `:5065`, `:5388`, `:5397`, `:5569`.

There are also **ffmpeg version gates**:

| Field | Version | Line |
|:--|:--|--:|
| `_minFFmpegOclCuTonemapMode` | 5.1.3 | 76 |
| `_minFFmpegAdvancedTonemapMode` | 7.0.1 | 82 |
| `_minFFmpegQsvVppTonemapOption` | 7.0.1 | 84 |
| `_maxFFmpegCkeyPauseSupported` | 6.1 | `TranscodeManager.cs:55` |

**Implication for the port:** the Go implementation must reproduce not just the argv logic but the
*probe* results that feed it. The differential harness therefore has to inject a fixed, synthetic
`IMediaEncoder` capability set rather than probing the host — otherwise CI results depend on
whatever GPU the runner has, which is exactly what we cannot afford.

## Full-support gates

Whole-pipeline availability predicates, each of which can demote a chain to a fallback:

`IsVaapiSupported` (`:270`), `IsVaapiFullSupported` (`:282`), `IsRkmppFullSupported` (`:295`),
`IsVideoToolboxFullSupported` (`:335`), plus `IsOpenclFullSupported` (referenced `:5960`).

## Port strategy implication

The dimensionality is roughly:

```
10 pipelines
  x (tonemap: off | sw | hw | vulkan | intel-vpp | videotoolbox)
  x (deinterlace: off | sw | hw)
  x (subtitle: none | embed | burn-in)
  x (driver quirk flags: 5 booleans, not independent)
  x (ffmpeg version: 4 gates)
```

The product is large but **sparse** — most combinations are unreachable. The differential harness
(design doc §4) must enumerate the *reachable* combinations by driving real `DeviceProfile` +
`MediaSourceInfo` pairs through both implementations, not by enumerating the cross product.

This is the single most likely place for the project to fail. See design doc §9 for the
convergence question and the stop signal.
