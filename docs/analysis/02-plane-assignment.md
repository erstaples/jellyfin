# Plane assignment

| Plane | Operations | Distinct paths |
|:--|--:|--:|
| CONTROL | 251 | 198 |
| TRANSCODE-PINNED | 24 | 17 |
| TRANSCODE-CACHEABLE | 4 | 4 |
| OUT | 140 | 116 |
| **total** | **419** | **335** |


## TRANSCODE-PINNED

| Method | Route | Controller | In spec | Rationale |
|:--|:--|:--|:-:|:--|
| GET | `/Audio/{itemId}/stream` | Audio | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| HEAD | `/Audio/{itemId}/stream` | Audio | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| GET | `/Audio/{itemId}/stream.{container}` | Audio | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| HEAD | `/Audio/{itemId}/stream.{container}` | Audio | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| GET | `/Audio/{itemId}/hls1/{playlistId}/{segmentId}.{container}` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Audio/{itemId}/main.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Audio/{itemId}/master.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| HEAD | `/Audio/{itemId}/master.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Videos/{itemId}/hls1/{playlistId}/{segmentId}.{container}` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Videos/{itemId}/live.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Videos/{itemId}/main.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Videos/{itemId}/master.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| HEAD | `/Videos/{itemId}/master.m3u8` | DynamicHls | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Audio/{itemId}/hls/{segmentId}/stream.aac` | HlsSegment | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Audio/{itemId}/hls/{segmentId}/stream.mp3` | HlsSegment | no | HLS playlist/segment; bound to a live ffmpeg job |
| DELETE | `/Videos/ActiveEncodings` | HlsSegment | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Videos/{itemId}/hls/{playlistId}/stream.m3u8` | HlsSegment | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Videos/{itemId}/hls/{playlistId}/{segmentId}.{segmentContainer}` | HlsSegment | no | HLS playlist/segment; bound to a live ffmpeg job |
| GET | `/Audio/{itemId}/universal` | UniversalAudio | yes | Negotiates then streams/redirects; can spawn ffmpeg |
| HEAD | `/Audio/{itemId}/universal` | UniversalAudio | yes | Negotiates then streams/redirects; can spawn ffmpeg |
| GET | `/Videos/{itemId}/stream` | Videos | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| HEAD | `/Videos/{itemId}/stream` | Videos | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| GET | `/Videos/{itemId}/stream.{container}` | Videos | yes | Progressive stream; may spawn ffmpeg for the response lifetime |
| HEAD | `/Videos/{itemId}/stream.{container}` | Videos | yes | Progressive stream; may spawn ffmpeg for the response lifetime |

## TRANSCODE-CACHEABLE

| Method | Route | Controller | In spec | Rationale |
|:--|:--|:--|:-:|:--|
| GET | `/Videos/{itemId}/{mediaSourceId}/Subtitles/{index}/subtitles.m3u8` | Subtitle | yes | Subtitle extract/convert spawns ffmpeg; output cacheable |
| GET | `/Videos/{routeItemId}/{routeMediaSourceId}/Subtitles/{routeIndex}/Stream.{routeFormat}` | Subtitle | yes | Subtitle extract/convert spawns ffmpeg; output cacheable |
| GET | `/Videos/{routeItemId}/{routeMediaSourceId}/Subtitles/{routeIndex}/{routeStartPositionTicks}/Stream.{routeFormat}` | Subtitle | yes | Subtitle extract/convert spawns ffmpeg; output cacheable |
| GET | `/Videos/{videoId}/{mediaSourceId}/Attachments/{index}` | VideoAttachments | yes | Attachment extraction spawns ffmpeg; output cacheable |

## OUT

| Method | Route | Controller | In spec | Rationale |
|:--|:--|:--|:-:|:--|
| GET | `/System/ActivityLog/Entries` | ActivityLog | yes | Admin activity feed; web-only surface |
| GET | `/Backup` | Backup | yes | Server backup/restore; operator concern |
| POST | `/Backup/Create` | Backup | yes | Server backup/restore; operator concern |
| GET | `/Backup/Manifest` | Backup | yes | Server backup/restore; operator concern |
| POST | `/Backup/Restore` | Backup | yes | Server backup/restore; operator concern |
| GET | `/Branding/Css` | Branding | yes | jellyfin-web branding asset |
| GET | `/Branding/Css.css` | Branding | yes | jellyfin-web branding asset |
| GET | `/Channels` | Channels | yes | Channels - explicit non-goal |
| GET | `/Channels/Features` | Channels | yes | Channels - explicit non-goal |
| GET | `/Channels/Items/Latest` | Channels | yes | Channels - explicit non-goal |
| GET | `/Channels/{channelId}/Features` | Channels | yes | Channels - explicit non-goal |
| GET | `/Channels/{channelId}/Items` | Channels | yes | Channels - explicit non-goal |
| GET | `/System/Configuration` | Configuration | yes | Server config -> ConfigMap/CRD |
| POST | `/System/Configuration` | Configuration | yes | Server config -> ConfigMap/CRD |
| POST | `/System/Configuration/Branding` | Configuration | yes | Server config -> ConfigMap/CRD |
| GET | `/System/Configuration/MetadataOptions/Default` | Configuration | yes | Server config -> ConfigMap/CRD |
| GET | `/System/Configuration/{key}` | Configuration | yes | Server config -> ConfigMap/CRD |
| POST | `/System/Configuration/{key}` | Configuration | yes | Server config -> ConfigMap/CRD |
| GET | `/web/ConfigurationPage` | Dashboard | yes | jellyfin-web dashboard - we do not serve web |
| GET | `/web/ConfigurationPages` | Dashboard | yes | jellyfin-web dashboard - we do not serve web |
| GET | `/Environment/DefaultDirectoryBrowser` | Environment | yes | Filesystem browser for web library picker; CRD instead |
| GET | `/Environment/DirectoryContents` | Environment | yes | Filesystem browser for web library picker; CRD instead |
| GET | `/Environment/Drives` | Environment | yes | Filesystem browser for web library picker; CRD instead |
| GET | `/Environment/ParentPath` | Environment | yes | Filesystem browser for web library picker; CRD instead |
| POST | `/Environment/ValidatePath` | Environment | yes | Filesystem browser for web library picker; CRD instead |
| DELETE | `/Branding/Splashscreen` | Image | yes | jellyfin-web branding asset |
| GET | `/Branding/Splashscreen` | Image | yes | jellyfin-web branding asset |
| POST | `/Branding/Splashscreen` | Image | yes | jellyfin-web branding asset |
| GET | `/Albums/{itemId}/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| GET | `/Artists/InstantMix` | InstantMix | no | Instant mix - explicit non-goal |
| GET | `/Artists/{itemId}/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| GET | `/Items/{itemId}/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| GET | `/MusicGenres/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| GET | `/MusicGenres/{name}/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| GET | `/Playlists/{itemId}/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| GET | `/Songs/{itemId}/InstantMix` | InstantMix | yes | Instant mix - explicit non-goal |
| DELETE | `/Library/VirtualFolders` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| GET | `/Library/VirtualFolders` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| POST | `/Library/VirtualFolders` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| POST | `/Library/VirtualFolders/LibraryOptions` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| POST | `/Library/VirtualFolders/Name` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| DELETE | `/Library/VirtualFolders/Paths` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| POST | `/Library/VirtualFolders/Paths` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| POST | `/Library/VirtualFolders/Paths/Update` | LibraryStructure | yes | Virtual folder CRUD -> library CRD |
| GET | `/LiveTv/ChannelMappingOptions` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/ChannelMappings` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Channels` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Channels/{channelId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/GuideInfo` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Info` | LiveTv | yes | LiveTv - explicit non-goal |
| DELETE | `/LiveTv/ListingProviders` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/ListingProviders` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/ListingProviders/Default` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/ListingProviders/Lineups` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/ListingProviders/SchedulesDirect/Countries` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/LiveRecordings/{recordingId}/stream` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/LiveStreamFiles/{streamId}/stream.{container}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Programs` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/Programs` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Programs/Recommended` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Programs/{programId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Recordings` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Recordings/Folders` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Recordings/Groups` | LiveTv | no | LiveTv - explicit non-goal |
| GET | `/LiveTv/Recordings/Series` | LiveTv | no | LiveTv - explicit non-goal |
| DELETE | `/LiveTv/Recordings/{recordingId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Recordings/{recordingId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/SeriesTimers` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/SeriesTimers` | LiveTv | yes | LiveTv - explicit non-goal |
| DELETE | `/LiveTv/SeriesTimers/{timerId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/SeriesTimers/{timerId}` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/SeriesTimers/{timerId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Timers` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/Timers` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Timers/Defaults` | LiveTv | yes | LiveTv - explicit non-goal |
| DELETE | `/LiveTv/Timers/{timerId}` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Timers/{timerId}` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/Timers/{timerId}` | LiveTv | yes | LiveTv - explicit non-goal |
| DELETE | `/LiveTv/TunerHosts` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/TunerHosts` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/TunerHosts/Types` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Tuners/Discover` | LiveTv | yes | LiveTv - explicit non-goal |
| GET | `/LiveTv/Tuners/Discvover` | LiveTv | yes | LiveTv - explicit non-goal |
| POST | `/LiveTv/Tuners/{tunerId}/Reset` | LiveTv | yes | LiveTv - explicit non-goal |
| DELETE | `/Audio/{itemId}/Lyrics` | Lyrics | yes | Lyrics - explicit non-goal |
| GET | `/Audio/{itemId}/Lyrics` | Lyrics | yes | Lyrics - explicit non-goal |
| POST | `/Audio/{itemId}/Lyrics` | Lyrics | yes | Lyrics - explicit non-goal |
| GET | `/Audio/{itemId}/RemoteSearch/Lyrics` | Lyrics | yes | Lyrics - explicit non-goal |
| POST | `/Audio/{itemId}/RemoteSearch/Lyrics/{lyricId}` | Lyrics | yes | Lyrics - explicit non-goal |
| GET | `/Providers/Lyrics/{lyricId}` | Lyrics | yes | Lyrics - explicit non-goal |
| GET | `/Packages` | Package | yes | Plugin repository/install - non-goal |
| POST | `/Packages/Installed/{name}` | Package | yes | Plugin repository/install - non-goal |
| DELETE | `/Packages/Installing/{packageId}` | Package | yes | Plugin repository/install - non-goal |
| GET | `/Packages/{name}` | Package | yes | Plugin repository/install - non-goal |
| GET | `/Repositories` | Package | yes | Plugin repository/install - non-goal |
| POST | `/Repositories` | Package | yes | Plugin repository/install - non-goal |
| GET | `/Plugins` | Plugins | yes | Plugins - explicit non-goal |
| DELETE | `/Plugins/{pluginId}` | Plugins | yes | Plugins - explicit non-goal |
| GET | `/Plugins/{pluginId}/Configuration` | Plugins | yes | Plugins - explicit non-goal |
| POST | `/Plugins/{pluginId}/Configuration` | Plugins | yes | Plugins - explicit non-goal |
| POST | `/Plugins/{pluginId}/Manifest` | Plugins | yes | Plugins - explicit non-goal |
| DELETE | `/Plugins/{pluginId}/{version}` | Plugins | yes | Plugins - explicit non-goal |
| POST | `/Plugins/{pluginId}/{version}/Disable` | Plugins | yes | Plugins - explicit non-goal |
| POST | `/Plugins/{pluginId}/{version}/Enable` | Plugins | yes | Plugins - explicit non-goal |
| GET | `/Plugins/{pluginId}/{version}/Image` | Plugins | yes | Plugins - explicit non-goal |
| GET | `/ScheduledTasks` | ScheduledTasks | yes | Tasks become K8s CronJobs; managed via kubectl |
| DELETE | `/ScheduledTasks/Running/{taskId}` | ScheduledTasks | yes | Tasks become K8s CronJobs; managed via kubectl |
| POST | `/ScheduledTasks/Running/{taskId}` | ScheduledTasks | yes | Tasks become K8s CronJobs; managed via kubectl |
| GET | `/ScheduledTasks/{taskId}` | ScheduledTasks | yes | Tasks become K8s CronJobs; managed via kubectl |
| POST | `/ScheduledTasks/{taskId}/Triggers` | ScheduledTasks | yes | Tasks become K8s CronJobs; managed via kubectl |
| POST | `/Startup/Complete` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| GET | `/Startup/Configuration` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| POST | `/Startup/Configuration` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| GET | `/Startup/FirstUser` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| POST | `/Startup/RemoteAccess` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| GET | `/Startup/User` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| POST | `/Startup/User` | Startup | yes | First-run wizard is web-only; setup via CLI/CRD |
| POST | `/SyncPlay/Buffering` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Join` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Leave` | SyncPlay | yes | SyncPlay - explicit non-goal |
| GET | `/SyncPlay/List` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/MovePlaylistItem` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/New` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/NextItem` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Pause` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Ping` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/PreviousItem` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Queue` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Ready` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/RemoveFromPlaylist` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Seek` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/SetIgnoreWait` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/SetNewQueue` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/SetPlaylistItem` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/SetRepeatMode` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/SetShuffleMode` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Stop` | SyncPlay | yes | SyncPlay - explicit non-goal |
| POST | `/SyncPlay/Unpause` | SyncPlay | yes | SyncPlay - explicit non-goal |
| GET | `/SyncPlay/{id:guid}` | SyncPlay | yes | SyncPlay - explicit non-goal |
| GET | `/GetUtcTime` | TimeSync | yes | SyncPlay clock sync only - non-goal |

## CONTROL

| Method | Route | Controller | In spec | Rationale |
|:--|:--|:--|:-:|:--|
| GET | `/Auth/Keys` | ApiKey | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Auth/Keys` | ApiKey | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Auth/Keys/{key}` | ApiKey | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Artists` | Artists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Artists/AlbumArtists` | Artists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Artists/{name}` | Artists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Branding/Configuration` | Branding | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/ClientLog/Document` | ClientLog | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Collections` | Collection | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Collections/{collectionId}/Items` | Collection | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Collections/{collectionId}/Items` | Collection | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Devices` | Devices | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Devices` | Devices | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Devices/Info` | Devices | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Devices/Options` | Devices | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Devices/Options` | Devices | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/DisplayPreferences/{displayPreferencesId}` | DisplayPreferences | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/DisplayPreferences/{displayPreferencesId}` | DisplayPreferences | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/Filters` | Filter | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/Filters2` | Filter | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Genres` | Genres | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Genres/{genreName}` | Genres | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Artists/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Artists/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Genres/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Genres/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Genres/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Genres/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Images` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Items/{itemId}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Items/{itemId}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/Images/{imageType}/{imageIndex}/Index` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Images/{imageType}/{imageIndex}/{tag}/{format}/{maxWidth}/{maxHeight}/{percentPlayed}/{unplayedCount}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Items/{itemId}/Images/{imageType}/{imageIndex}/{tag}/{format}/{maxWidth}/{maxHeight}/{percentPlayed}/{unplayedCount}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/MusicGenres/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/MusicGenres/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/MusicGenres/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/MusicGenres/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Persons/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Persons/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Persons/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Persons/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Studios/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Studios/{name}/Images/{imageType}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Studios/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Studios/{name}/Images/{imageType}/{imageIndex}` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/UserImage` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/UserImage` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/UserImage` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/UserImage` | Image | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}/Images/{imageType}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Images/{imageType}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Users/{userId}/Images/{imageType}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Images/{imageType}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Images/{imageType}/{imageIndex}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| HEAD | `/Users/{userId}/Images/{imageType}/{imageIndex}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}/Images/{imageType}/{index}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Images/{imageType}/{index}` | Image | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/Apply/{itemId}` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/Book` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/BoxSet` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/Movie` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/MusicAlbum` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/MusicArtist` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/MusicVideo` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/Person` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/Series` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/RemoteSearch/Trailer` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/ExternalIdInfos` | ItemLookup | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/Refresh` | ItemRefresh | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}` | ItemUpdate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/ContentType` | ItemUpdate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/MetadataEditor` | ItemUpdate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items` | Items | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/UserItems/Resume` | Items | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/UserItems/{itemId}/UserData` | Items | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/UserItems/{itemId}/UserData` | Items | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items` | Items | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/Resume` | Items | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/{itemId}/UserData` | Items | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Items/{itemId}/UserData` | Items | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Albums/{itemId}/Similar` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Artists/{itemId}/Similar` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Items` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/Counts` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Items/{itemId}` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Ancestors` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Collections` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Download` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/File` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Similar` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/ThemeMedia` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/ThemeSongs` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/ThemeVideos` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Libraries/AvailableOptions` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Library/Media/Updated` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Library/MediaFolders` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Library/Movies/Added` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Library/Movies/Updated` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Library/PhysicalPaths` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Library/Refresh` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Library/Series/Added` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Library/Series/Updated` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Movies/{itemId}/Similar` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Shows/{itemId}/Similar` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Trailers/{itemId}/Similar` | Library | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Localization/Countries` | Localization | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Localization/Cultures` | Localization | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Localization/Options` | Localization | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Localization/ParentalRatings` | Localization | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/PlaybackInfo` | MediaInfo | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/PlaybackInfo` | MediaInfo | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/LiveStreams/Close` | MediaInfo | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/LiveStreams/Open` | MediaInfo | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Playback/BitrateTest` | MediaInfo | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/MediaSegments/{itemId}` | MediaSegments | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Movies/Recommendations` | Movies | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/MusicGenres` | MusicGenres | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/MusicGenres/{genreName}` | MusicGenres | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Persons` | Persons | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Persons/{name}` | Persons | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Playlists` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Playlists/{playlistId}` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Playlists/{playlistId}` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Playlists/{playlistId}/Items` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Playlists/{playlistId}/Items` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Playlists/{playlistId}/Items` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Playlists/{playlistId}/Items/{itemId}/Move/{newIndex}` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Playlists/{playlistId}/Users` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Playlists/{playlistId}/Users/{userId}` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Playlists/{playlistId}/Users/{userId}` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Playlists/{playlistId}/Users/{userId}` | Playlists | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/PlayingItems/{itemId}` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/PlayingItems/{itemId}` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/PlayingItems/{itemId}/Progress` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Playing` | Playstate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Playing/Ping` | Playstate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Playing/Progress` | Playstate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Playing/Stopped` | Playstate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/UserPlayedItems/{itemId}` | Playstate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/UserPlayedItems/{itemId}` | Playstate | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}/PlayedItems/{itemId}` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/PlayedItems/{itemId}` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}/PlayingItems/{itemId}` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/PlayingItems/{itemId}` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/PlayingItems/{itemId}/Progress` | Playstate | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/QuickConnect/Authorize` | QuickConnect | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/QuickConnect/Connect` | QuickConnect | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/QuickConnect/Enabled` | QuickConnect | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/QuickConnect/Initiate` | QuickConnect | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/RemoteImages` | RemoteImage | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/RemoteImages/Download` | RemoteImage | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/RemoteImages/Providers` | RemoteImage | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Search/Hints` | Search | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Auth/PasswordResetProviders` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Auth/Providers` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Sessions` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Capabilities` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Capabilities/Full` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Logout` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/Viewing` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/Command` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/Command/{command}` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/Message` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/Playing` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/Playing/{command}` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/System/{command}` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Sessions/{sessionId}/User/{userId}` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/User/{userId}` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Sessions/{sessionId}/Viewing` | Session | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Studios` | Studios | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Studios/{name}` | Studios | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/FallbackFont/Fonts` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/FallbackFont/Fonts/{name}` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/RemoteSearch/Subtitles/{language}` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Items/{itemId}/RemoteSearch/Subtitles/{subtitleId}` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Providers/Subtitles/Subtitles/{subtitleId}` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Videos/{itemId}/Subtitles` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Videos/{itemId}/Subtitles/{index}` | Subtitle | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/Suggestions` | Suggestions | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Suggestions` | Suggestions | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Endpoint` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Info` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Info/Public` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Info/Storage` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Logs` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Logs/Log` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/System/Ping` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/System/Ping` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/System/Restart` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/System/Shutdown` | System | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Trailers` | Trailers | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Videos/{itemId}/Trickplay/{width}/tiles.m3u8` | Trickplay | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Videos/{itemId}/Trickplay/{width}/{index}.jpg` | Trickplay | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Shows/NextUp` | TvShows | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Shows/Upcoming` | TvShows | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Shows/{seriesId}/Episodes` | TvShows | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Shows/{seriesId}/Seasons` | TvShows | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/AuthenticateByName` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/AuthenticateWithQuickConnect` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/Configuration` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/ForgotPassword` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/ForgotPassword/Pin` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/Me` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/New` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/Password` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/Public` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}` | User | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Authenticate` | User | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Configuration` | User | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Password` | User | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Policy` | User | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/Latest` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/Root` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/Intros` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/LocalTrailers` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Items/{itemId}/SpecialFeatures` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/UserFavoriteItems/{itemId}` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/UserFavoriteItems/{itemId}` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/UserItems/{itemId}/Rating` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/UserItems/{itemId}/Rating` | UserLibrary | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}/FavoriteItems/{itemId}` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/FavoriteItems/{itemId}` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/Latest` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/Root` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/{itemId}` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/{itemId}/Intros` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/{itemId}/LocalTrailers` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Users/{userId}/Items/{itemId}/Rating` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Users/{userId}/Items/{itemId}/Rating` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Items/{itemId}/SpecialFeatures` | UserLibrary | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/UserViews` | UserViews | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/UserViews/GroupingOptions` | UserViews | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/GroupingOptions` | UserViews | no | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Users/{userId}/Views` | UserViews | no | DB read/write returning JSON or a static file; no long-lived resource |
| POST | `/Videos/MergeVersions` | Videos | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Videos/{itemId}/AdditionalParts` | Videos | yes | DB read/write returning JSON or a static file; no long-lived resource |
| DELETE | `/Videos/{itemId}/AlternateSources` | Videos | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Years` | Years | yes | DB read/write returning JSON or a static file; no long-lived resource |
| GET | `/Years/{year}` | Years | yes | DB read/write returning JSON or a static file; no long-lived resource |
