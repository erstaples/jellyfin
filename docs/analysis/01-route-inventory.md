# Route inventory and spec delta

Generated from `Jellyfin.Api/Controllers/*.cs` at commit `71ab342` (AssemblyVersion 12.0.0, `SharedVersion.cs:3`).

`IN SPEC` is derived from `[ApiExplorerSettings(IgnoreApi = true)]` at method or class scope, which is
exactly what Swashbuckle honours when generating the published document
(`Jellyfin.Server/Extensions/ApiServiceCollectionExtensions.cs:196`). `DEPR` is `[Obsolete]` at method or class scope.

| # | Method | Route | Controller | In spec | Depr | Plane | Source |
|--:|:--|:--|:--|:-:|:-:|:--|:--|
| 1 | GET | `/Albums/{itemId}/InstantMix` | InstantMix | yes |  | OUT | `InstantMixController.cs:112` |
| 2 | GET | `/Albums/{itemId}/Similar` | Library | yes |  | CONTROL | `LibraryController.cs:802` |
| 3 | GET | `/Artists` | Artists | yes | yes | CONTROL | `ArtistsController.cs:88` |
| 4 | GET | `/Artists/AlbumArtists` | Artists | yes | yes | CONTROL | `ArtistsController.cs:260` |
| 5 | GET | `/Artists/InstantMix` | InstantMix | no | yes | OUT | `InstantMixController.cs:320` |
| 6 | GET | `/Artists/{itemId}/InstantMix` | InstantMix | yes |  | OUT | `InstantMixController.cs:234` |
| 7 | GET | `/Artists/{itemId}/Similar` | Library | yes |  | CONTROL | `LibraryController.cs:800` |
| 8 | GET | `/Artists/{name}` | Artists | yes | yes | CONTROL | `ArtistsController.cs:402` |
| 9 | GET | `/Artists/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:786` |
| 10 | HEAD | `/Artists/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:787` |
| 11 | DELETE | `/Audio/{itemId}/Lyrics` | Lyrics | yes |  | OUT | `LyricsController.cs:152` |
| 12 | GET | `/Audio/{itemId}/Lyrics` | Lyrics | yes |  | OUT | `LyricsController.cs:67` |
| 13 | POST | `/Audio/{itemId}/Lyrics` | Lyrics | yes |  | OUT | `LyricsController.cs:97` |
| 14 | GET | `/Audio/{itemId}/RemoteSearch/Lyrics` | Lyrics | yes |  | OUT | `LyricsController.cs:176` |
| 15 | POST | `/Audio/{itemId}/RemoteSearch/Lyrics/{lyricId}` | Lyrics | yes |  | OUT | `LyricsController.cs:200` |
| 16 | GET | `/Audio/{itemId}/hls/{segmentId}/stream.aac` | HlsSegment | no |  | TRANSCODE-PINNED | `HlsSegmentController.cs:56` |
| 17 | GET | `/Audio/{itemId}/hls/{segmentId}/stream.mp3` | HlsSegment | no |  | TRANSCODE-PINNED | `HlsSegmentController.cs:55` |
| 18 | GET | `/Audio/{itemId}/hls1/{playlistId}/{segmentId}.{container}` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:1269` |
| 19 | GET | `/Audio/{itemId}/main.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:915` |
| 20 | GET | `/Audio/{itemId}/master.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:578` |
| 21 | HEAD | `/Audio/{itemId}/master.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:579` |
| 22 | GET | `/Audio/{itemId}/stream` | Audio | yes |  | TRANSCODE-PINNED | `AudioController.cs:88` |
| 23 | HEAD | `/Audio/{itemId}/stream` | Audio | yes |  | TRANSCODE-PINNED | `AudioController.cs:89` |
| 24 | GET | `/Audio/{itemId}/stream.{container}` | Audio | yes |  | TRANSCODE-PINNED | `AudioController.cs:252` |
| 25 | HEAD | `/Audio/{itemId}/stream.{container}` | Audio | yes |  | TRANSCODE-PINNED | `AudioController.cs:253` |
| 26 | GET | `/Audio/{itemId}/universal` | UniversalAudio | yes |  | TRANSCODE-PINNED | `UniversalAudioController.cs:92` |
| 27 | HEAD | `/Audio/{itemId}/universal` | UniversalAudio | yes |  | TRANSCODE-PINNED | `UniversalAudioController.cs:93` |
| 28 | GET | `/Auth/Keys` | ApiKey | yes |  | CONTROL | `ApiKeyController.cs:36` |
| 29 | POST | `/Auth/Keys` | ApiKey | yes |  | CONTROL | `ApiKeyController.cs:52` |
| 30 | DELETE | `/Auth/Keys/{key}` | ApiKey | yes |  | CONTROL | `ApiKeyController.cs:68` |
| 31 | GET | `/Auth/PasswordResetProviders` | Session | yes |  | CONTROL | `SessionController.cs:447` |
| 32 | GET | `/Auth/Providers` | Session | yes |  | CONTROL | `SessionController.cs:433` |
| 33 | GET | `/Backup` | Backup | yes |  | OUT | `BackupController.cs:79` |
| 34 | POST | `/Backup/Create` | Backup | yes |  | OUT | `BackupController.cs:42` |
| 35 | GET | `/Backup/Manifest` | Backup | yes |  | OUT | `BackupController.cs:96` |
| 36 | POST | `/Backup/Restore` | Backup | yes |  | OUT | `BackupController.cs:57` |
| 37 | GET | `/Branding/Configuration` | Branding | yes |  | CONTROL | `BrandingController.cs:30` |
| 38 | GET | `/Branding/Css` | Branding | yes |  | OUT | `BrandingController.cs:55` |
| 39 | GET | `/Branding/Css.css` | Branding | yes |  | OUT | `BrandingController.cs:56` |
| 40 | DELETE | `/Branding/Splashscreen` | Image | yes |  | OUT | `ImageController.cs:1758` |
| 41 | GET | `/Branding/Splashscreen` | Image | yes |  | OUT | `ImageController.cs:1647` |
| 42 | POST | `/Branding/Splashscreen` | Image | yes |  | OUT | `ImageController.cs:1721` |
| 43 | GET | `/Channels` | Channels | yes |  | OUT | `ChannelsController.cs:56` |
| 44 | GET | `/Channels/Features` | Channels | yes |  | OUT | `ChannelsController.cs:83` |
| 45 | GET | `/Channels/Items/Latest` | Channels | yes |  | OUT | `ChannelsController.cs:165` |
| 46 | GET | `/Channels/{channelId}/Features` | Channels | yes |  | OUT | `ChannelsController.cs:96` |
| 47 | GET | `/Channels/{channelId}/Items` | Channels | yes |  | OUT | `ChannelsController.cs:119` |
| 48 | POST | `/ClientLog/Document` | ClientLog | yes |  | CONTROL | `ClientLogController.cs:45` |
| 49 | POST | `/Collections` | Collection | yes |  | CONTROL | `CollectionController.cs:49` |
| 50 | DELETE | `/Collections/{collectionId}/Items` | Collection | yes |  | CONTROL | `CollectionController.cs:102` |
| 51 | POST | `/Collections/{collectionId}/Items` | Collection | yes |  | CONTROL | `CollectionController.cs:85` |
| 52 | DELETE | `/Devices` | Devices | yes |  | CONTROL | `DevicesController.cs:125` |
| 53 | GET | `/Devices` | Devices | yes |  | CONTROL | `DevicesController.cs:51` |
| 54 | GET | `/Devices/Info` | Devices | yes |  | CONTROL | `DevicesController.cs:66` |
| 55 | GET | `/Devices/Options` | Devices | yes |  | CONTROL | `DevicesController.cs:87` |
| 56 | POST | `/Devices/Options` | Devices | yes |  | CONTROL | `DevicesController.cs:108` |
| 57 | GET | `/DisplayPreferences/{displayPreferencesId}` | DisplayPreferences | yes |  | CONTROL | `DisplayPreferencesController.cs:48` |
| 58 | POST | `/DisplayPreferences/{displayPreferencesId}` | DisplayPreferences | yes |  | CONTROL | `DisplayPreferencesController.cs:112` |
| 59 | GET | `/Environment/DefaultDirectoryBrowser` | Environment | yes |  | OUT | `EnvironmentController.cs:176` |
| 60 | GET | `/Environment/DirectoryContents` | Environment | yes |  | OUT | `EnvironmentController.cs:48` |
| 61 | GET | `/Environment/Drives` | Environment | yes |  | OUT | `EnvironmentController.cs:135` |
| 62 | GET | `/Environment/ParentPath` | Environment | yes |  | OUT | `EnvironmentController.cs:147` |
| 63 | POST | `/Environment/ValidatePath` | Environment | yes |  | OUT | `EnvironmentController.cs:76` |
| 64 | GET | `/FallbackFont/Fonts` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:497` |
| 65 | GET | `/FallbackFont/Fonts/{name}` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:548` |
| 66 | GET | `/Genres` | Genres | yes |  | CONTROL | `GenresController.cs:74` |
| 67 | GET | `/Genres/{genreName}` | Genres | yes |  | CONTROL | `GenresController.cs:157` |
| 68 | GET | `/Genres/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:864` |
| 69 | HEAD | `/Genres/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:865` |
| 70 | GET | `/Genres/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:942` |
| 71 | HEAD | `/Genres/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:943` |
| 72 | GET | `/GetUtcTime` | TimeSync | yes |  | OUT | `TimeSyncController.cs:20` |
| 73 | DELETE | `/Items` | Library | yes |  | CONTROL | `LibraryController.cs:406` |
| 74 | GET | `/Items` | Items | yes |  | CONTROL | `ItemsController.cs:171` |
| 75 | GET | `/Items/Counts` | Library | yes |  | CONTROL | `LibraryController.cs:453` |
| 76 | GET | `/Items/Filters` | Filter | yes |  | CONTROL | `FilterController.cs:53` |
| 77 | GET | `/Items/Filters2` | Filter | yes |  | CONTROL | `FilterController.cs:112` |
| 78 | GET | `/Items/Latest` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:521` |
| 79 | POST | `/Items/RemoteSearch/Apply/{itemId}` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:244` |
| 80 | POST | `/Items/RemoteSearch/Book` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:224` |
| 81 | POST | `/Items/RemoteSearch/BoxSet` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:155` |
| 82 | POST | `/Items/RemoteSearch/Movie` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:87` |
| 83 | POST | `/Items/RemoteSearch/MusicAlbum` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:189` |
| 84 | POST | `/Items/RemoteSearch/MusicArtist` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:172` |
| 85 | POST | `/Items/RemoteSearch/MusicVideo` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:121` |
| 86 | POST | `/Items/RemoteSearch/Person` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:206` |
| 87 | POST | `/Items/RemoteSearch/Series` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:138` |
| 88 | POST | `/Items/RemoteSearch/Trailer` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:104` |
| 89 | GET | `/Items/Root` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:126` |
| 90 | GET | `/Items/Suggestions` | Suggestions | yes |  | CONTROL | `SuggestionsController.cs:60` |
| 91 | DELETE | `/Items/{itemId}` | Library | yes |  | CONTROL | `LibraryController.cs:362` |
| 92 | GET | `/Items/{itemId}` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:76` |
| 93 | POST | `/Items/{itemId}` | ItemUpdate | yes |  | CONTROL | `ItemUpdateController.cs:72` |
| 94 | GET | `/Items/{itemId}/Ancestors` | Library | yes |  | CONTROL | `LibraryController.cs:487` |
| 95 | GET | `/Items/{itemId}/Collections` | Library | yes |  | CONTROL | `LibraryController.cs:735` |
| 96 | POST | `/Items/{itemId}/ContentType` | ItemUpdate | yes |  | CONTROL | `ItemUpdateController.cs:207` |
| 97 | GET | `/Items/{itemId}/Download` | Library | yes |  | CONTROL | `LibraryController.cs:669` |
| 98 | GET | `/Items/{itemId}/ExternalIdInfos` | ItemLookup | yes |  | CONTROL | `ItemLookupController.cs:63` |
| 99 | GET | `/Items/{itemId}/File` | Library | yes |  | CONTROL | `LibraryController.cs:109` |
| 100 | GET | `/Items/{itemId}/Images` | Image | yes |  | CONTROL | `ImageController.cs:467` |
| 101 | DELETE | `/Items/{itemId}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:297` |
| 102 | GET | `/Items/{itemId}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:552` |
| 103 | HEAD | `/Items/{itemId}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:553` |
| 104 | POST | `/Items/{itemId}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:352` |
| 105 | DELETE | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:325` |
| 106 | GET | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:630` |
| 107 | HEAD | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:631` |
| 108 | POST | `/Items/{itemId}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:395` |
| 109 | POST | `/Items/{itemId}/Images/{imageType}/{imageIndex}/Index` | Image | yes |  | CONTROL | `ImageController.cs:440` |
| 110 | GET | `/Items/{itemId}/Images/{imageType}/{imageIndex}/{tag}/{format}/{maxWidth}/{maxHeight}/{percentPlayed}/{unplayedCount}` | Image | yes |  | CONTROL | `ImageController.cs:708` |
| 111 | HEAD | `/Items/{itemId}/Images/{imageType}/{imageIndex}/{tag}/{format}/{maxWidth}/{maxHeight}/{percentPlayed}/{unplayedCount}` | Image | yes |  | CONTROL | `ImageController.cs:709` |
| 112 | GET | `/Items/{itemId}/InstantMix` | InstantMix | yes |  | OUT | `InstantMixController.cs:277` |
| 113 | GET | `/Items/{itemId}/Intros` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:163` |
| 114 | GET | `/Items/{itemId}/LocalTrailers` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:410` |
| 115 | GET | `/Items/{itemId}/MetadataEditor` | ItemUpdate | yes |  | CONTROL | `ItemUpdateController.cs:145` |
| 116 | GET | `/Items/{itemId}/PlaybackInfo` | MediaInfo | yes |  | CONTROL | `MediaInfoController.cs:72` |
| 117 | POST | `/Items/{itemId}/PlaybackInfo` | MediaInfo | yes |  | CONTROL | `MediaInfoController.cs:116` |
| 118 | POST | `/Items/{itemId}/Refresh` | ItemRefresh | yes |  | CONTROL | `ItemRefreshController.cs:58` |
| 119 | GET | `/Items/{itemId}/RemoteImages` | RemoteImage | yes |  | CONTROL | `RemoteImageController.cs:62` |
| 120 | POST | `/Items/{itemId}/RemoteImages/Download` | RemoteImage | yes |  | CONTROL | `RemoteImageController.cs:151` |
| 121 | GET | `/Items/{itemId}/RemoteImages/Providers` | RemoteImage | yes |  | CONTROL | `RemoteImageController.cs:127` |
| 122 | GET | `/Items/{itemId}/RemoteSearch/Subtitles/{language}` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:118` |
| 123 | POST | `/Items/{itemId}/RemoteSearch/Subtitles/{subtitleId}` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:144` |
| 124 | GET | `/Items/{itemId}/Similar` | Library | yes |  | CONTROL | `LibraryController.cs:801` |
| 125 | GET | `/Items/{itemId}/SpecialFeatures` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:460` |
| 126 | GET | `/Items/{itemId}/ThemeMedia` | Library | yes |  | CONTROL | `LibraryController.cs:294` |
| 127 | GET | `/Items/{itemId}/ThemeSongs` | Library | yes |  | CONTROL | `LibraryController.cs:147` |
| 128 | GET | `/Items/{itemId}/ThemeVideos` | Library | yes |  | CONTROL | `LibraryController.cs:221` |
| 129 | GET | `/Libraries/AvailableOptions` | Library | yes |  | CONTROL | `LibraryController.cs:864` |
| 130 | POST | `/Library/Media/Updated` | Library | yes |  | CONTROL | `LibraryController.cs:648` |
| 131 | GET | `/Library/MediaFolders` | Library | yes |  | CONTROL | `LibraryController.cs:547` |
| 132 | POST | `/Library/Movies/Added` | Library | yes |  | CONTROL | `LibraryController.cs:606` |
| 133 | POST | `/Library/Movies/Updated` | Library | yes |  | CONTROL | `LibraryController.cs:607` |
| 134 | GET | `/Library/PhysicalPaths` | Library | yes |  | CONTROL | `LibraryController.cs:532` |
| 135 | POST | `/Library/Refresh` | Library | yes |  | CONTROL | `LibraryController.cs:337` |
| 136 | POST | `/Library/Series/Added` | Library | yes |  | CONTROL | `LibraryController.cs:576` |
| 137 | POST | `/Library/Series/Updated` | Library | yes |  | CONTROL | `LibraryController.cs:577` |
| 138 | DELETE | `/Library/VirtualFolders` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:106` |
| 139 | GET | `/Library/VirtualFolders` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:58` |
| 140 | POST | `/Library/VirtualFolders` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:75` |
| 141 | POST | `/Library/VirtualFolders/LibraryOptions` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:339` |
| 142 | POST | `/Library/VirtualFolders/Name` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:129` |
| 143 | DELETE | `/Library/VirtualFolders/Paths` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:294` |
| 144 | POST | `/Library/VirtualFolders/Paths` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:229` |
| 145 | POST | `/Library/VirtualFolders/Paths/Update` | LibraryStructure | yes |  | OUT | `LibraryStructureController.cs:272` |
| 146 | POST | `/LiveStreams/Close` | MediaInfo | yes |  | CONTROL | `MediaInfoController.cs:314` |
| 147 | POST | `/LiveStreams/Open` | MediaInfo | yes |  | CONTROL | `MediaInfoController.cs:269` |
| 148 | GET | `/LiveTv/ChannelMappingOptions` | LiveTv | yes |  | OUT | `LiveTvController.cs:1066` |
| 149 | POST | `/LiveTv/ChannelMappings` | LiveTv | yes |  | OUT | `LiveTvController.cs:1078` |
| 150 | GET | `/LiveTv/Channels` | LiveTv | yes |  | OUT | `LiveTvController.cs:138` |
| 151 | GET | `/LiveTv/Channels/{channelId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:218` |
| 152 | GET | `/LiveTv/GuideInfo` | LiveTv | yes |  | OUT | `LiveTvController.cs:938` |
| 153 | GET | `/LiveTv/Info` | LiveTv | yes |  | OUT | `LiveTvController.cs:102` |
| 154 | DELETE | `/LiveTv/ListingProviders` | LiveTv | yes |  | OUT | `LiveTvController.cs:1017` |
| 155 | POST | `/LiveTv/ListingProviders` | LiveTv | yes |  | OUT | `LiveTvController.cs:993` |
| 156 | GET | `/LiveTv/ListingProviders/Default` | LiveTv | yes |  | OUT | `LiveTvController.cs:976` |
| 157 | GET | `/LiveTv/ListingProviders/Lineups` | LiveTv | yes |  | OUT | `LiveTvController.cs:1035` |
| 158 | GET | `/LiveTv/ListingProviders/SchedulesDirect/Countries` | LiveTv | yes |  | OUT | `LiveTvController.cs:1050` |
| 159 | GET | `/LiveTv/LiveRecordings/{recordingId}/stream` | LiveTv | yes |  | OUT | `LiveTvController.cs:1118` |
| 160 | GET | `/LiveTv/LiveStreamFiles/{streamId}/stream.{container}` | LiveTv | yes |  | OUT | `LiveTvController.cs:1145` |
| 161 | GET | `/LiveTv/Programs` | LiveTv | yes |  | OUT | `LiveTvController.cs:542` |
| 162 | POST | `/LiveTv/Programs` | LiveTv | yes |  | OUT | `LiveTvController.cs:626` |
| 163 | GET | `/LiveTv/Programs/Recommended` | LiveTv | yes |  | OUT | `LiveTvController.cs:694` |
| 164 | GET | `/LiveTv/Programs/{programId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:749` |
| 165 | GET | `/LiveTv/Recordings` | LiveTv | yes |  | OUT | `LiveTvController.cs:265` |
| 166 | GET | `/LiveTv/Recordings/Folders` | LiveTv | yes |  | OUT | `LiveTvController.cs:382` |
| 167 | GET | `/LiveTv/Recordings/Groups` | LiveTv | no | yes | OUT | `LiveTvController.cs:366` |
| 168 | GET | `/LiveTv/Recordings/Series` | LiveTv | no | yes | OUT | `LiveTvController.cs:336` |
| 169 | DELETE | `/LiveTv/Recordings/{recordingId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:778` |
| 170 | GET | `/LiveTv/Recordings/{recordingId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:406` |
| 171 | GET | `/LiveTv/SeriesTimers` | LiveTv | yes |  | OUT | `LiveTvController.cs:873` |
| 172 | POST | `/LiveTv/SeriesTimers` | LiveTv | yes |  | OUT | `LiveTvController.cs:924` |
| 173 | DELETE | `/LiveTv/SeriesTimers/{timerId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:893` |
| 174 | GET | `/LiveTv/SeriesTimers/{timerId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:851` |
| 175 | POST | `/LiveTv/SeriesTimers/{timerId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:909` |
| 176 | GET | `/LiveTv/Timers` | LiveTv | yes |  | OUT | `LiveTvController.cs:488` |
| 177 | POST | `/LiveTv/Timers` | LiveTv | yes |  | OUT | `LiveTvController.cs:835` |
| 178 | GET | `/LiveTv/Timers/Defaults` | LiveTv | yes |  | OUT | `LiveTvController.cs:468` |
| 179 | DELETE | `/LiveTv/Timers/{timerId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:804` |
| 180 | GET | `/LiveTv/Timers/{timerId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:452` |
| 181 | POST | `/LiveTv/Timers/{timerId}` | LiveTv | yes |  | OUT | `LiveTvController.cs:820` |
| 182 | DELETE | `/LiveTv/TunerHosts` | LiveTv | yes |  | OUT | `LiveTvController.cs:962` |
| 183 | POST | `/LiveTv/TunerHosts` | LiveTv | yes |  | OUT | `LiveTvController.cs:950` |
| 184 | GET | `/LiveTv/TunerHosts/Types` | LiveTv | yes |  | OUT | `LiveTvController.cs:1089` |
| 185 | GET | `/LiveTv/Tuners/Discover` | LiveTv | yes |  | OUT | `LiveTvController.cs:1102` |
| 186 | GET | `/LiveTv/Tuners/Discvover` | LiveTv | yes |  | OUT | `LiveTvController.cs:1101` |
| 187 | POST | `/LiveTv/Tuners/{tunerId}/Reset` | LiveTv | yes |  | OUT | `LiveTvController.cs:435` |
| 188 | GET | `/Localization/Countries` | Localization | yes |  | CONTROL | `LocalizationController.cs:54` |
| 189 | GET | `/Localization/Cultures` | Localization | yes |  | CONTROL | `LocalizationController.cs:35` |
| 190 | GET | `/Localization/Options` | Localization | yes |  | CONTROL | `LocalizationController.cs:78` |
| 191 | GET | `/Localization/ParentalRatings` | Localization | yes |  | CONTROL | `LocalizationController.cs:66` |
| 192 | GET | `/MediaSegments/{itemId}` | MediaSegments | yes |  | CONTROL | `MediaSegmentsController.cs:46` |
| 193 | GET | `/Movies/Recommendations` | Movies | yes |  | CONTROL | `MoviesController.cs:59` |
| 194 | GET | `/Movies/{itemId}/Similar` | Library | yes |  | CONTROL | `LibraryController.cs:804` |
| 195 | GET | `/MusicGenres` | MusicGenres | no | yes | CONTROL | `MusicGenresController.cs:74` |
| 196 | GET | `/MusicGenres/InstantMix` | InstantMix | yes | yes | OUT | `InstantMixController.cs:360` |
| 197 | GET | `/MusicGenres/{genreName}` | MusicGenres | yes | yes | CONTROL | `MusicGenresController.cs:147` |
| 198 | GET | `/MusicGenres/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:1020` |
| 199 | HEAD | `/MusicGenres/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:1021` |
| 200 | GET | `/MusicGenres/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:1098` |
| 201 | HEAD | `/MusicGenres/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:1099` |
| 202 | GET | `/MusicGenres/{name}/InstantMix` | InstantMix | yes | yes | OUT | `InstantMixController.cs:197` |
| 203 | GET | `/Packages` | Package | yes |  | OUT | `PackageController.cs:71` |
| 204 | POST | `/Packages/Installed/{name}` | Package | yes |  | OUT | `PackageController.cs:90` |
| 205 | DELETE | `/Packages/Installing/{packageId}` | Package | yes |  | OUT | `PackageController.cs:129` |
| 206 | GET | `/Packages/{name}` | Package | yes |  | OUT | `PackageController.cs:45` |
| 207 | GET | `/Persons` | Persons | yes |  | CONTROL | `PersonsController.cs:71` |
| 208 | GET | `/Persons/{name}` | Persons | yes |  | CONTROL | `PersonsController.cs:135` |
| 209 | GET | `/Persons/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:1176` |
| 210 | HEAD | `/Persons/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:1177` |
| 211 | GET | `/Persons/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:1254` |
| 212 | HEAD | `/Persons/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:1255` |
| 213 | GET | `/Playback/BitrateTest` | MediaInfo | yes |  | CONTROL | `MediaInfoController.cs:328` |
| 214 | DELETE | `/PlayingItems/{itemId}` | Playstate | no | yes | CONTROL | `PlaystateController.cs:445` |
| 215 | POST | `/PlayingItems/{itemId}` | Playstate | no | yes | CONTROL | `PlaystateController.cs:275` |
| 216 | POST | `/PlayingItems/{itemId}/Progress` | Playstate | no | yes | CONTROL | `PlaystateController.cs:355` |
| 217 | POST | `/Playlists` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:76` |
| 218 | GET | `/Playlists/{itemId}/InstantMix` | InstantMix | yes |  | OUT | `InstantMixController.cs:155` |
| 219 | GET | `/Playlists/{playlistId}` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:163` |
| 220 | POST | `/Playlists/{playlistId}` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:117` |
| 221 | DELETE | `/Playlists/{playlistId}/Items` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:446` |
| 222 | GET | `/Playlists/{playlistId}/Items` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:509` |
| 223 | POST | `/Playlists/{playlistId}/Items` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:369` |
| 224 | POST | `/Playlists/{playlistId}/Items/{itemId}/Move/{newIndex}` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:408` |
| 225 | GET | `/Playlists/{playlistId}/Users` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:195` |
| 226 | DELETE | `/Playlists/{playlistId}/Users/{userId}` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:323` |
| 227 | GET | `/Playlists/{playlistId}/Users/{userId}` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:226` |
| 228 | POST | `/Playlists/{playlistId}/Users/{userId}` | Playlists | yes |  | CONTROL | `PlaylistsController.cs:277` |
| 229 | GET | `/Plugins` | Plugins | yes |  | OUT | `PluginsController.cs:52` |
| 230 | DELETE | `/Plugins/{pluginId}` | Plugins | yes |  | OUT | `PluginsController.cs:137` |
| 231 | GET | `/Plugins/{pluginId}/Configuration` | Plugins | yes |  | OUT | `PluginsController.cs:164` |
| 232 | POST | `/Plugins/{pluginId}/Configuration` | Plugins | yes |  | OUT | `PluginsController.cs:188` |
| 233 | POST | `/Plugins/{pluginId}/Manifest` | Plugins | yes |  | OUT | `PluginsController.cs:268` |
| 234 | DELETE | `/Plugins/{pluginId}/{version}` | Plugins | yes |  | OUT | `PluginsController.cs:115` |
| 235 | POST | `/Plugins/{pluginId}/{version}/Disable` | Plugins | yes |  | OUT | `PluginsController.cs:92` |
| 236 | POST | `/Plugins/{pluginId}/{version}/Enable` | Plugins | yes |  | OUT | `PluginsController.cs:69` |
| 237 | GET | `/Plugins/{pluginId}/{version}/Image` | Plugins | yes |  | OUT | `PluginsController.cs:217` |
| 238 | GET | `/Providers/Lyrics/{lyricId}` | Lyrics | yes |  | OUT | `LyricsController.cs:231` |
| 239 | GET | `/Providers/Subtitles/Subtitles/{subtitleId}` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:179` |
| 240 | POST | `/QuickConnect/Authorize` | QuickConnect | yes |  | CONTROL | `QuickConnectController.cs:104` |
| 241 | GET | `/QuickConnect/Connect` | QuickConnect | yes |  | CONTROL | `QuickConnectController.cs:77` |
| 242 | GET | `/QuickConnect/Enabled` | QuickConnect | yes |  | CONTROL | `QuickConnectController.cs:41` |
| 243 | POST | `/QuickConnect/Initiate` | QuickConnect | yes |  | CONTROL | `QuickConnectController.cs:54` |
| 244 | GET | `/Repositories` | Package | yes |  | OUT | `PackageController.cs:143` |
| 245 | POST | `/Repositories` | Package | yes |  | OUT | `PackageController.cs:156` |
| 246 | GET | `/ScheduledTasks` | ScheduledTasks | yes |  | OUT | `ScheduledTasksController.cs:38` |
| 247 | DELETE | `/ScheduledTasks/Running/{taskId}` | ScheduledTasks | yes |  | OUT | `ScheduledTasksController.cs:119` |
| 248 | POST | `/ScheduledTasks/Running/{taskId}` | ScheduledTasks | yes |  | OUT | `ScheduledTasksController.cs:95` |
| 249 | GET | `/ScheduledTasks/{taskId}` | ScheduledTasks | yes |  | OUT | `ScheduledTasksController.cs:72` |
| 250 | POST | `/ScheduledTasks/{taskId}/Triggers` | ScheduledTasks | yes |  | OUT | `ScheduledTasksController.cs:144` |
| 251 | GET | `/Search/Hints` | Search | yes |  | CONTROL | `SearchController.cs:80` |
| 252 | GET | `/Sessions` | Session | yes |  | CONTROL | `SessionController.cs:52` |
| 253 | POST | `/Sessions/Capabilities` | Session | yes |  | CONTROL | `SessionController.cs:345` |
| 254 | POST | `/Sessions/Capabilities/Full` | Session | yes |  | CONTROL | `SessionController.cs:377` |
| 255 | POST | `/Sessions/Logout` | Session | yes |  | CONTROL | `SessionController.cs:419` |
| 256 | POST | `/Sessions/Playing` | Playstate | yes |  | CONTROL | `PlaystateController.cs:201` |
| 257 | POST | `/Sessions/Playing/Ping` | Playstate | yes |  | CONTROL | `PlaystateController.cs:233` |
| 258 | POST | `/Sessions/Playing/Progress` | Playstate | yes |  | CONTROL | `PlaystateController.cs:217` |
| 259 | POST | `/Sessions/Playing/Stopped` | Playstate | yes |  | CONTROL | `PlaystateController.cs:247` |
| 260 | POST | `/Sessions/Viewing` | Session | yes |  | CONTROL | `SessionController.cs:401` |
| 261 | POST | `/Sessions/{sessionId}/Command` | Session | yes |  | CONTROL | `SessionController.cs:247` |
| 262 | POST | `/Sessions/{sessionId}/Command/{command}` | Session | yes |  | CONTROL | `SessionController.cs:219` |
| 263 | POST | `/Sessions/{sessionId}/Message` | Session | yes |  | CONTROL | `SessionController.cs:277` |
| 264 | POST | `/Sessions/{sessionId}/Playing` | Session | yes |  | CONTROL | `SessionController.cs:119` |
| 265 | POST | `/Sessions/{sessionId}/Playing/{command}` | Session | yes |  | CONTROL | `SessionController.cs:162` |
| 266 | POST | `/Sessions/{sessionId}/System/{command}` | Session | yes |  | CONTROL | `SessionController.cs:193` |
| 267 | DELETE | `/Sessions/{sessionId}/User/{userId}` | Session | yes |  | CONTROL | `SessionController.cs:324` |
| 268 | POST | `/Sessions/{sessionId}/User/{userId}` | Session | yes |  | CONTROL | `SessionController.cs:306` |
| 269 | POST | `/Sessions/{sessionId}/Viewing` | Session | yes |  | CONTROL | `SessionController.cs:80` |
| 270 | GET | `/Shows/NextUp` | TvShows | yes |  | CONTROL | `TvShowsController.cs:75` |
| 271 | GET | `/Shows/Upcoming` | TvShows | yes |  | CONTROL | `TvShowsController.cs:138` |
| 272 | GET | `/Shows/{itemId}/Similar` | Library | yes |  | CONTROL | `LibraryController.cs:803` |
| 273 | GET | `/Shows/{seriesId}/Episodes` | TvShows | yes |  | CONTROL | `TvShowsController.cs:202` |
| 274 | GET | `/Shows/{seriesId}/Seasons` | TvShows | yes |  | CONTROL | `TvShowsController.cs:332` |
| 275 | GET | `/Songs/{itemId}/InstantMix` | InstantMix | yes |  | OUT | `InstantMixController.cs:69` |
| 276 | POST | `/Startup/Complete` | Startup | yes |  | OUT | `StartupController.cs:40` |
| 277 | GET | `/Startup/Configuration` | Startup | yes | yes | OUT | `StartupController.cs:54` |
| 278 | POST | `/Startup/Configuration` | Startup | yes | yes | OUT | `StartupController.cs:74` |
| 279 | GET | `/Startup/FirstUser` | Startup | yes | yes | OUT | `StartupController.cs:110` |
| 280 | POST | `/Startup/RemoteAccess` | Startup | yes | yes | OUT | `StartupController.cs:93` |
| 281 | GET | `/Startup/User` | Startup | yes | yes | OUT | `StartupController.cs:109` |
| 282 | POST | `/Startup/User` | Startup | yes |  | OUT | `StartupController.cs:133` |
| 283 | GET | `/Studios` | Studios | yes |  | CONTROL | `StudiosController.cs:70` |
| 284 | GET | `/Studios/{name}` | Studios | yes |  | CONTROL | `StudiosController.cs:140` |
| 285 | GET | `/Studios/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:1332` |
| 286 | HEAD | `/Studios/{name}/Images/{imageType}` | Image | yes |  | CONTROL | `ImageController.cs:1333` |
| 287 | GET | `/Studios/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:1410` |
| 288 | HEAD | `/Studios/{name}/Images/{imageType}/{imageIndex}` | Image | yes |  | CONTROL | `ImageController.cs:1411` |
| 289 | POST | `/SyncPlay/Buffering` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:296` |
| 290 | POST | `/SyncPlay/Join` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:71` |
| 291 | POST | `/SyncPlay/Leave` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:88` |
| 292 | GET | `/SyncPlay/List` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:104` |
| 293 | POST | `/SyncPlay/MovePlaylistItem` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:194` |
| 294 | POST | `/SyncPlay/New` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:54` |
| 295 | POST | `/SyncPlay/NextItem` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:358` |
| 296 | POST | `/SyncPlay/Pause` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:245` |
| 297 | POST | `/SyncPlay/Ping` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:430` |
| 298 | POST | `/SyncPlay/PreviousItem` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:376` |
| 299 | POST | `/SyncPlay/Queue` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:212` |
| 300 | POST | `/SyncPlay/Ready` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:318` |
| 301 | POST | `/SyncPlay/RemoveFromPlaylist` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:176` |
| 302 | POST | `/SyncPlay/Seek` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:278` |
| 303 | POST | `/SyncPlay/SetIgnoreWait` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:340` |
| 304 | POST | `/SyncPlay/SetNewQueue` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:137` |
| 305 | POST | `/SyncPlay/SetPlaylistItem` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:158` |
| 306 | POST | `/SyncPlay/SetRepeatMode` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:394` |
| 307 | POST | `/SyncPlay/SetShuffleMode` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:412` |
| 308 | POST | `/SyncPlay/Stop` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:261` |
| 309 | POST | `/SyncPlay/Unpause` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:229` |
| 310 | GET | `/SyncPlay/{id:guid}` | SyncPlay | yes |  | OUT | `SyncPlayController.cs:120` |
| 311 | GET | `/System/ActivityLog/Entries` | ActivityLog | yes |  | OUT | `ActivityLogController.cs:55` |
| 312 | GET | `/System/Configuration` | Configuration | yes |  | OUT | `ConfigurationController.cs:49` |
| 313 | POST | `/System/Configuration` | Configuration | yes |  | OUT | `ConfigurationController.cs:62` |
| 314 | POST | `/System/Configuration/Branding` | Configuration | yes |  | OUT | `ConfigurationController.cs:128` |
| 315 | GET | `/System/Configuration/MetadataOptions/Default` | Configuration | yes |  | OUT | `ConfigurationController.cs:114` |
| 316 | GET | `/System/Configuration/{key}` | Configuration | yes |  | OUT | `ConfigurationController.cs:77` |
| 317 | POST | `/System/Configuration/{key}` | Configuration | yes |  | OUT | `ConfigurationController.cs:92` |
| 318 | GET | `/System/Endpoint` | System | yes |  | CONTROL | `SystemController.cs:185` |
| 319 | GET | `/System/Info` | System | yes |  | CONTROL | `SystemController.cs:67` |
| 320 | GET | `/System/Info/Public` | System | yes |  | CONTROL | `SystemController.cs:92` |
| 321 | GET | `/System/Info/Storage` | System | yes |  | CONTROL | `SystemController.cs:80` |
| 322 | GET | `/System/Logs` | System | yes |  | CONTROL | `SystemController.cs:146` |
| 323 | GET | `/System/Logs/Log` | System | yes |  | CONTROL | `SystemController.cs:206` |
| 324 | GET | `/System/Ping` | System | yes |  | CONTROL | `SystemController.cs:102` |
| 325 | POST | `/System/Ping` | System | yes |  | CONTROL | `SystemController.cs:103` |
| 326 | POST | `/System/Restart` | System | yes |  | CONTROL | `SystemController.cs:114` |
| 327 | POST | `/System/Shutdown` | System | yes |  | CONTROL | `SystemController.cs:130` |
| 328 | GET | `/Trailers` | Trailers | yes | yes | CONTROL | `TrailersController.cs:123` |
| 329 | GET | `/Trailers/{itemId}/Similar` | Library | yes |  | CONTROL | `LibraryController.cs:805` |
| 330 | DELETE | `/UserFavoriteItems/{itemId}` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:262` |
| 331 | POST | `/UserFavoriteItems/{itemId}` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:214` |
| 332 | DELETE | `/UserImage` | Image | yes |  | CONTROL | `ImageController.cs:205` |
| 333 | GET | `/UserImage` | Image | yes |  | CONTROL | `ImageController.cs:1475` |
| 334 | HEAD | `/UserImage` | Image | yes |  | CONTROL | `ImageController.cs:1476` |
| 335 | POST | `/UserImage` | Image | yes |  | CONTROL | `ImageController.cs:96` |
| 336 | GET | `/UserItems/Resume` | Items | yes |  | CONTROL | `ItemsController.cs:921` |
| 337 | DELETE | `/UserItems/{itemId}/Rating` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:310` |
| 338 | POST | `/UserItems/{itemId}/Rating` | UserLibrary | yes |  | CONTROL | `UserLibraryController.cs:359` |
| 339 | GET | `/UserItems/{itemId}/UserData` | Items | yes |  | CONTROL | `ItemsController.cs:1072` |
| 340 | POST | `/UserItems/{itemId}/UserData` | Items | yes |  | CONTROL | `ItemsController.cs:1128` |
| 341 | DELETE | `/UserPlayedItems/{itemId}` | Playstate | yes |  | CONTROL | `PlaystateController.cs:139` |
| 342 | POST | `/UserPlayedItems/{itemId}` | Playstate | yes |  | CONTROL | `PlaystateController.cs:72` |
| 343 | GET | `/UserViews` | UserViews | yes |  | CONTROL | `UserViewsController.cs:65` |
| 344 | GET | `/UserViews/GroupingOptions` | UserViews | yes |  | CONTROL | `UserViewsController.cs:128` |
| 345 | GET | `/Users` | User | yes |  | CONTROL | `UserController.cs:91` |
| 346 | POST | `/Users` | User | yes |  | CONTROL | `UserController.cs:351` |
| 347 | POST | `/Users/AuthenticateByName` | User | yes |  | CONTROL | `UserController.cs:209` |
| 348 | POST | `/Users/AuthenticateWithQuickConnect` | User | yes |  | CONTROL | `UserController.cs:245` |
| 349 | POST | `/Users/Configuration` | User | yes |  | CONTROL | `UserController.cs:467` |
| 350 | POST | `/Users/ForgotPassword` | User | yes |  | CONTROL | `UserController.cs:541` |
| 351 | POST | `/Users/ForgotPassword/Pin` | User | yes |  | CONTROL | `UserController.cs:566` |
| 352 | GET | `/Users/Me` | User | yes |  | CONTROL | `UserController.cs:581` |
| 353 | POST | `/Users/New` | User | yes |  | CONTROL | `UserController.cs:517` |
| 354 | POST | `/Users/Password` | User | yes |  | CONTROL | `UserController.cs:270` |
| 355 | GET | `/Users/Public` | User | yes |  | CONTROL | `UserController.cs:107` |
| 356 | DELETE | `/Users/{userId}` | User | yes |  | CONTROL | `UserController.cs:151` |
| 357 | GET | `/Users/{userId}` | User | yes |  | CONTROL | `UserController.cs:127` |
| 358 | POST | `/Users/{userId}` | User | no | yes | CONTROL | `UserController.cs:391` |
| 359 | POST | `/Users/{userId}/Authenticate` | User | no | yes | CONTROL | `UserController.cs:178` |
| 360 | POST | `/Users/{userId}/Configuration` | User | no | yes | CONTROL | `UserController.cs:500` |
| 361 | DELETE | `/Users/{userId}/FavoriteItems/{itemId}` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:294` |
| 362 | POST | `/Users/{userId}/FavoriteItems/{itemId}` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:246` |
| 363 | GET | `/Users/{userId}/GroupingOptions` | UserViews | no | yes | CONTROL | `UserViewsController.cs:163` |
| 364 | DELETE | `/Users/{userId}/Images/{imageType}` | Image | no | yes | CONTROL | `ImageController.cs:251` |
| 365 | GET | `/Users/{userId}/Images/{imageType}` | Image | no | yes | CONTROL | `ImageController.cs:1554` |
| 366 | HEAD | `/Users/{userId}/Images/{imageType}` | Image | no | yes | CONTROL | `ImageController.cs:1555` |
| 367 | POST | `/Users/{userId}/Images/{imageType}` | Image | no | yes | CONTROL | `ImageController.cs:159` |
| 368 | GET | `/Users/{userId}/Images/{imageType}/{imageIndex}` | Image | no | yes | CONTROL | `ImageController.cs:1610` |
| 369 | HEAD | `/Users/{userId}/Images/{imageType}/{imageIndex}` | Image | no | yes | CONTROL | `ImageController.cs:1611` |
| 370 | DELETE | `/Users/{userId}/Images/{imageType}/{index}` | Image | no | yes | CONTROL | `ImageController.cs:274` |
| 371 | POST | `/Users/{userId}/Images/{imageType}/{index}` | Image | no | yes | CONTROL | `ImageController.cs:182` |
| 372 | GET | `/Users/{userId}/Items` | Items | no | yes | CONTROL | `ItemsController.cs:721` |
| 373 | GET | `/Users/{userId}/Items/Latest` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:613` |
| 374 | GET | `/Users/{userId}/Items/Resume` | Items | no | yes | CONTROL | `ItemsController.cs:1027` |
| 375 | GET | `/Users/{userId}/Items/Root` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:148` |
| 376 | GET | `/Users/{userId}/Items/{itemId}` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:111` |
| 377 | GET | `/Users/{userId}/Items/{itemId}/Intros` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:198` |
| 378 | GET | `/Users/{userId}/Items/{itemId}/LocalTrailers` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:444` |
| 379 | DELETE | `/Users/{userId}/Items/{itemId}/Rating` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:342` |
| 380 | POST | `/Users/{userId}/Items/{itemId}/Rating` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:393` |
| 381 | GET | `/Users/{userId}/Items/{itemId}/SpecialFeatures` | UserLibrary | no | yes | CONTROL | `UserLibraryController.cs:496` |
| 382 | GET | `/Users/{userId}/Items/{itemId}/UserData` | Items | no | yes | CONTROL | `ItemsController.cs:1109` |
| 383 | POST | `/Users/{userId}/Items/{itemId}/UserData` | Items | no | yes | CONTROL | `ItemsController.cs:1169` |
| 384 | POST | `/Users/{userId}/Password` | User | no | yes | CONTROL | `UserController.cs:330` |
| 385 | DELETE | `/Users/{userId}/PlayedItems/{itemId}` | Playstate | no | yes | CONTROL | `PlaystateController.cs:185` |
| 386 | POST | `/Users/{userId}/PlayedItems/{itemId}` | Playstate | no | yes | CONTROL | `PlaystateController.cs:120` |
| 387 | DELETE | `/Users/{userId}/PlayingItems/{itemId}` | Playstate | no | yes | CONTROL | `PlaystateController.cs:490` |
| 388 | POST | `/Users/{userId}/PlayingItems/{itemId}` | Playstate | no | yes | CONTROL | `PlaystateController.cs:321` |
| 389 | POST | `/Users/{userId}/PlayingItems/{itemId}/Progress` | Playstate | no | yes | CONTROL | `PlaystateController.cs:413` |
| 390 | POST | `/Users/{userId}/Policy` | User | yes |  | CONTROL | `UserController.cs:412` |
| 391 | GET | `/Users/{userId}/Suggestions` | Suggestions | no | yes | CONTROL | `SuggestionsController.cs:114` |
| 392 | GET | `/Users/{userId}/Views` | UserViews | no | yes | CONTROL | `UserViewsController.cs:107` |
| 393 | DELETE | `/Videos/ActiveEncodings` | HlsSegment | no |  | TRANSCODE-PINNED | `HlsSegmentController.cs:103` |
| 394 | POST | `/Videos/MergeVersions` | Videos | yes |  | CONTROL | `VideosController.cs:183` |
| 395 | GET | `/Videos/{itemId}/AdditionalParts` | Videos | yes |  | CONTROL | `VideosController.cs:94` |
| 396 | DELETE | `/Videos/{itemId}/AlternateSources` | Videos | yes |  | CONTROL | `VideosController.cs:139` |
| 397 | POST | `/Videos/{itemId}/Subtitles` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:420` |
| 398 | DELETE | `/Videos/{itemId}/Subtitles/{index}` | Subtitle | yes |  | CONTROL | `SubtitleController.cs:91` |
| 399 | GET | `/Videos/{itemId}/Trickplay/{width}/tiles.m3u8` | Trickplay | yes |  | CONTROL | `TrickplayController.cs:50` |
| 400 | GET | `/Videos/{itemId}/Trickplay/{width}/{index}.jpg` | Trickplay | yes |  | CONTROL | `TrickplayController.cs:79` |
| 401 | GET | `/Videos/{itemId}/hls/{playlistId}/stream.m3u8` | HlsSegment | no |  | TRANSCODE-PINNED | `HlsSegmentController.cs:79` |
| 402 | GET | `/Videos/{itemId}/hls/{playlistId}/{segmentId}.{segmentContainer}` | HlsSegment | no |  | TRANSCODE-PINNED | `HlsSegmentController.cs:126` |
| 403 | GET | `/Videos/{itemId}/hls1/{playlistId}/{segmentId}.{container}` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:1087` |
| 404 | GET | `/Videos/{itemId}/live.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:165` |
| 405 | GET | `/Videos/{itemId}/main.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:746` |
| 406 | GET | `/Videos/{itemId}/master.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:405` |
| 407 | HEAD | `/Videos/{itemId}/master.m3u8` | DynamicHls | no |  | TRANSCODE-PINNED | `DynamicHlsController.cs:406` |
| 408 | GET | `/Videos/{itemId}/stream` | Videos | yes |  | TRANSCODE-PINNED | `VideosController.cs:314` |
| 409 | HEAD | `/Videos/{itemId}/stream` | Videos | yes |  | TRANSCODE-PINNED | `VideosController.cs:315` |
| 410 | GET | `/Videos/{itemId}/stream.{container}` | Videos | yes |  | TRANSCODE-PINNED | `VideosController.cs:552` |
| 411 | HEAD | `/Videos/{itemId}/stream.{container}` | Videos | yes |  | TRANSCODE-PINNED | `VideosController.cs:553` |
| 412 | GET | `/Videos/{itemId}/{mediaSourceId}/Subtitles/{index}/subtitles.m3u8` | Subtitle | yes |  | TRANSCODE-CACHEABLE | `SubtitleController.cs:338` |
| 413 | GET | `/Videos/{routeItemId}/{routeMediaSourceId}/Subtitles/{routeIndex}/Stream.{routeFormat}` | Subtitle | yes |  | TRANSCODE-CACHEABLE | `SubtitleController.cs:208` |
| 414 | GET | `/Videos/{routeItemId}/{routeMediaSourceId}/Subtitles/{routeIndex}/{routeStartPositionTicks}/Stream.{routeFormat}` | Subtitle | yes |  | TRANSCODE-CACHEABLE | `SubtitleController.cs:295` |
| 415 | GET | `/Videos/{videoId}/{mediaSourceId}/Attachments/{index}` | VideoAttachments | yes |  | TRANSCODE-CACHEABLE | `VideoAttachmentsController.cs:50` |
| 416 | GET | `/Years` | Years | yes |  | CONTROL | `YearsController.cs:72` |
| 417 | GET | `/Years/{year}` | Years | yes |  | CONTROL | `YearsController.cs:173` |
| 418 | GET | `/web/ConfigurationPage` | Dashboard | yes |  | OUT | `DashboardController.cs:73` |
| 419 | GET | `/web/ConfigurationPages` | Dashboard | yes |  | OUT | `DashboardController.cs:49` |
