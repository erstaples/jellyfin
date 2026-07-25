#!/usr/bin/env python3
"""Assign every extracted route to a plane and emit docs/analysis artifacts."""
import json
from collections import defaultdict, Counter

R = json.load(open('/tmp/claude-0/-home-user-jellyfin/d8ab225f-58cc-51b3-90a7-6b5c0513bee4/scratchpad/routes.json'))

# ---------------------------------------------------------------- plane rules
# Ordered rules: (predicate, plane, rationale). First match wins.
CTRL_OUT = {
    'LiveTvController':        ('OUT', 'LiveTv - explicit non-goal'),
    'SyncPlayController':      ('OUT', 'SyncPlay - explicit non-goal'),
    'TimeSyncController':      ('OUT', 'SyncPlay clock sync only - non-goal'),
    'PluginsController':       ('OUT', 'Plugins - explicit non-goal'),
    'PackageController':       ('OUT', 'Plugin repository/install - non-goal'),
    'ChannelsController':      ('OUT', 'Channels - explicit non-goal'),
    'LyricsController':        ('OUT', 'Lyrics - explicit non-goal'),
    'InstantMixController':    ('OUT', 'Instant mix - explicit non-goal'),
    'DashboardController':     ('OUT', 'jellyfin-web dashboard - we do not serve web'),
    'StartupController':       ('OUT', 'First-run wizard is web-only; setup via CLI/CRD'),
    'EnvironmentController':   ('OUT', 'Filesystem browser for web library picker; CRD instead'),
    'BackupController':        ('OUT', 'Server backup/restore; operator concern'),
    'ScheduledTasksController':('OUT', 'Tasks become K8s CronJobs; managed via kubectl'),
    'LibraryStructureController':('OUT','Virtual folder CRUD -> library CRD'),
    'ConfigurationController': ('OUT', 'Server config -> ConfigMap/CRD'),
    'ActivityLogController':   ('OUT', 'Admin activity feed; web-only surface'),
}

def classify(x):
    r, c, m = x['route'], x['controller'], x['method']

    # ---- transcode plane: session-pinned (owns an ffmpeg process + scratch dir)
    if c in ('DynamicHlsController', 'HlsSegmentController'):
        return ('TRANSCODE-PINNED', 'HLS playlist/segment; bound to a live ffmpeg job')
    if r in ('/Videos/{itemId}/stream', '/Videos/{itemId}/stream.{container}',
             '/Audio/{itemId}/stream', '/Audio/{itemId}/stream.{container}'):
        return ('TRANSCODE-PINNED', 'Progressive stream; may spawn ffmpeg for the response lifetime')
    if r == '/Audio/{itemId}/universal':
        return ('TRANSCODE-PINNED', 'Negotiates then streams/redirects; can spawn ffmpeg')

    # ---- transcode plane: stateless, content-addressed, cacheable
    if r.startswith('/Videos/{routeItemId}/{routeMediaSourceId}/Subtitles') \
       or r == '/Videos/{itemId}/{mediaSourceId}/Subtitles/{index}/subtitles.m3u8':
        return ('TRANSCODE-CACHEABLE', 'Subtitle extract/convert spawns ffmpeg; output cacheable')
    if 'Attachments' in r:
        return ('TRANSCODE-CACHEABLE', 'Attachment extraction spawns ffmpeg; output cacheable')

    # ---- explicit out-of-scope controllers
    if c in CTRL_OUT:
        return CTRL_OUT[c]

    # ---- per-route out-of-scope
    if r.startswith('/Branding/Css') or r == '/Branding/Splashscreen':
        return ('OUT', 'jellyfin-web branding asset')

    return ('CONTROL', 'DB read/write returning JSON or a static file; no long-lived resource')

for x in R:
    p, why = classify(x)
    x['plane'] = p
    x['rationale'] = why

# ---------------------------------------------------------------- artifact 1
def esc(s):
    return s.replace('|', r'\|')

lines = []
lines.append('# Route inventory and spec delta\n')
lines.append('Generated from `Jellyfin.Api/Controllers/*.cs` at commit `71ab342` (AssemblyVersion 12.0.0, `SharedVersion.cs:3`).\n')
lines.append('`IN SPEC` is derived from `[ApiExplorerSettings(IgnoreApi = true)]` at method or class scope, which is')
lines.append('exactly what Swashbuckle honours when generating the published document')
lines.append('(`Jellyfin.Server/Extensions/ApiServiceCollectionExtensions.cs:196`). `DEPR` is `[Obsolete]` at method or class scope.\n')
lines.append('| # | Method | Route | Controller | In spec | Depr | Plane | Source |')
lines.append('|--:|:--|:--|:--|:-:|:-:|:--|:--|')
rs = sorted(R, key=lambda x: (x['route'], x['method']))
for i, x in enumerate(rs, 1):
    src = f"{x['file'].split('/')[-1]}:{x['attr_line']}"
    lines.append('| {} | {} | `{}` | {} | {} | {} | {} | `{}` |'.format(
        i, x['method'], esc(x['route']), x['controller'][:-10],
        'no' if x['hidden'] else 'yes', 'yes' if x['obsolete'] else '',
        x['plane'], src))
open('docs/analysis/01-route-inventory.md', 'w').write('\n'.join(lines) + '\n')

# ---------------------------------------------------------------- artifact 2
lines = []
lines.append('# Plane assignment\n')
byplane = defaultdict(list)
for x in R:
    byplane[x['plane']].append(x)
lines.append('| Plane | Operations | Distinct paths |')
lines.append('|:--|--:|--:|')
for p in ('CONTROL', 'TRANSCODE-PINNED', 'TRANSCODE-CACHEABLE', 'OUT'):
    v = byplane[p]
    lines.append(f'| {p} | {len(v)} | {len({y["route"] for y in v})} |')
lines.append(f'| **total** | **{len(R)}** | **{len({y["route"] for y in R})}** |')
lines.append('')
for p in ('TRANSCODE-PINNED', 'TRANSCODE-CACHEABLE', 'OUT', 'CONTROL'):
    lines.append(f'\n## {p}\n')
    lines.append('| Method | Route | Controller | In spec | Rationale |')
    lines.append('|:--|:--|:--|:-:|:--|')
    for x in sorted(byplane[p], key=lambda y: (y['controller'], y['route'], y['method'])):
        lines.append('| {} | `{}` | {} | {} | {} |'.format(
            x['method'], esc(x['route']), x['controller'][:-10],
            'no' if x['hidden'] else 'yes', x['rationale']))
open('docs/analysis/02-plane-assignment.md', 'w').write('\n'.join(lines) + '\n')

json.dump(R, open('docs/analysis/routes.json', 'w'), indent=1)

# ---------------------------------------------------------------- console
print('operations           :', len(R))
print('distinct paths       :', len({x['route'] for x in R}))
print('in published spec    :', sum(1 for x in R if not x['hidden']),
      'ops /', len({x['route'] for x in R if not x['hidden']}), 'paths')
print('hidden from spec     :', sum(1 for x in R if x['hidden']), 'ops')
print('deprecated           :', sum(1 for x in R if x['obsolete']), 'ops')
print()
for p in ('CONTROL', 'TRANSCODE-PINNED', 'TRANSCODE-CACHEABLE', 'OUT'):
    v = byplane[p]
    print(f'{p:22}: {len(v):4} ops  {len({y["route"] for y in v}):4} paths')
print()
print('in-scope ops (CONTROL+TRANSCODE):',
      sum(1 for x in R if x['plane'] != 'OUT'))
print('hidden ops that are IN SCOPE    :',
      sum(1 for x in R if x['hidden'] and x['plane'] != 'OUT'))
