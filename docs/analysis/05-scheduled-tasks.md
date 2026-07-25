# Scheduled task inventory

19 `IScheduledTask` implementations. Each becomes a Kubernetes `CronJob` (or is dropped with the
feature it serves).

Trigger types are declared in each task's `GetDefaultTriggers()`. The four kinds in use are
`IntervalTrigger`, `DailyTrigger`, `StartupTrigger`, and "none declared" (manual / event-driven
only).

| Task | Key | Trigger | Depends on | Disposition |
|:--|:--|:--|:--|:--|
| `RefreshMediaLibraryTask` | `RefreshLibrary` | Interval | LibraryManager | **CronJob** — core |
| `PeopleValidationTask` | `RefreshPeople` | Interval | LibraryManager, DbContextFactory, FileSystem, ItemTypeLookup | **CronJob** — core |
| `ChapterImagesTask` | `RefreshChapterImages` | Daily | ChapterManager, LibraryManager, FileSystem, ApplicationPaths | **CronJob** — needs ffmpeg |
| `TrickplayImagesTask` | `RefreshTrickplayImages` | Daily | TrickplayManager, LibraryManager | **CronJob** — needs ffmpeg, GPU-optional |
| `TrickplayMoveImagesTask` | `MoveTrickplayImages` | none | TrickplayManager, LibraryManager | **CronJob** — manual only |
| `KeyframeExtractionScheduledTask` | `KeyframeExtraction` | none | KeyframeExtractor, LibraryManager | **CronJob** — needs ffmpeg; feeds HLS playlist generation |
| `MediaSegmentExtractionTask` | `TaskExtractMediaSegments` | Interval | MediaSegmentManager, LibraryManager | **CronJob** — intro/credit skip |
| `AudioNormalizationTask` | `AudioNormalization` | Interval | MediaEncoder, LibraryManager, ItemPersistenceService, ApplicationPaths | **CronJob** — needs ffmpeg |
| `SubtitleScheduledTask` | `DownloadSubtitles` | Interval | SubtitleManager, SubtitleProvider, LibraryManager, ServerConfigurationManager | **CronJob** — external network |
| `CleanupUserDataTask` | *(none)* | none | DbContextFactory | **CronJob** — DB maintenance |
| `CleanActivityLogTask` | `CleanActivityLog` | Interval | ActivityManager, ServerConfigurationManager | **CronJob** — trivial DELETE |
| `OptimizeDatabaseTask` | `OptimizeDatabaseTask` | Interval | JellyfinDatabaseProvider, LibraryManager | **Drop** — SQLite VACUUM; Postgres autovacuum replaces it |
| `DeleteTranscodeFileTask` | `DeleteTranscodeFiles` | Interval + Startup | ConfigurationManager, FileSystem | **Replace** — becomes transcode-pod-local GC, not a cluster CronJob |
| `DeleteCacheFileTask` | `DeleteCacheFiles` | Interval | ApplicationPaths, FileSystem | **Replace** — pod-local |
| `DeleteLogFileTask` | `CleanLogFiles` | Interval | ConfigurationManager, FileSystem | **Drop** — stdout + cluster log rotation |
| `PluginUpdateTask` | `PluginUpdates` | Interval + Startup | InstallationManager | **Drop** — plugins are a non-goal |
| `RefreshChannelsScheduledTask` | `RefreshInternetChannels` | Interval | ChannelManager, LibraryManager | **Drop** — channels are a non-goal |
| `RefreshGuideScheduledTask` | `RefreshGuide` | Interval | GuideManager, LiveTvManager, ConfigurationManager | **Drop** — LiveTv is a non-goal |
| `LyricScheduledTask` | `DownloadLyrics` | Interval | LyricManager, LibraryManager | **Drop** — lyrics are a non-goal |

## Summary

- **11 become CronJobs.**
- **3 become pod-local GC** (`DeleteTranscodeFileTask`, `DeleteCacheFileTask`, and the startup half
  of the transcode cleanup). These must not run cluster-wide: a CronJob deleting another pod's
  scratch dir would kill live sessions. On the transcode plane they belong in a sidecar or a
  periodic goroutine scoped to the pod's own scratch volume, keyed on the pod's active session set.
- **5 are dropped** with their non-goal features.

## Notes for the port

`ILocalizationManager` appears in nearly every task — it is only used to localise the task's
display name and category for the web dashboard. Since we do not serve jellyfin-web, this
dependency disappears entirely.

`DeleteTranscodeFileTask` carries a `StartupTrigger`, which in the current architecture cleans up
orphaned transcode output after an unclean shutdown. In the new design this is exactly the
behaviour we need on transcode-pod boot, since a pod that restarts has lost the in-memory job
list but not the scratch files. Preserve it as pod startup logic.

`OptimizeDatabaseTask` depends on `IJellyfinDatabaseProvider`, which is the SQLite abstraction.
This is the clearest single instance of a SQLite-shaped assumption in the task layer, and it is
dropped rather than ported.

## Trigger semantics needing a runtime experiment

`IntervalTrigger` in Jellyfin measures from *last completion*, not from a wall-clock schedule.
Kubernetes `CronJob` schedules on wall clock. For long-running tasks (library scan on a large
library) these differ materially: a scan that takes longer than its interval will queue up under
cron but self-space under Jellyfin. Confirm the actual interval semantics against the running
server and set `concurrencyPolicy: Forbid` on the corresponding CronJobs.
