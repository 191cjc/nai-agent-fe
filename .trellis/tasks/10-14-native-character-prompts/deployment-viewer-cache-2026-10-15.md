# Viewer Cache: Production Release

- Published: 2026-10-15 14:55 UTC (22:55 Asia/Shanghai).
- Source commit: b30250c4a55d862ad36be05add2a66060cfc6089
- URL: https://www.firesoul.cn/novelai/
- New web: /srv/www/novelai/releases/20261015T145554
- Previous web retained: /srv/www/novelai/releases/20261015T140424
- API unchanged: /srv/novelai/releases/20261015T140424, PID3184888.
- Deployment report: /tmp/nai-viewer-cache-deployment-report.json

## Verified Publication

- All 19 fresh build inputs equal both working and committed source bytes;
  the independently reviewed saved-results.ts freeze matches the build.
- Dist bytes equal the build report; installed release files are root-owned
  0644 under root-owned 0755 directories. Shared immutable assets are checked
  for collisions and remain available for previous open tabs/releases.
- Old web pointer, API pointer/PID/active state and old public HTML hash were
  checked before the atomic web switch. New public HTML and exact asset paths,
  JS/CSS hashes match the committed-source build.
- Public /novelai/api/health/ready reports ok; /aiqq/health and previous
  immutable JS/CSS return200 with matching hashes.
- Final web pointer is the new release; API pointer/PID/active state unchanged.
  No API restart, DB/schema migration, config/credential/unit/Nginx changes or
  paid calls. Background experiment execution is unaffected by this web update.
- Independent source/static checks and env-free build passed; see
  check-viewer-cache.md and viewer-cache-build-verification.md. No frontend/
  helper/browser automated tests. Real interaction remains operator acceptance.

## Exact Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| Web input map | 3df4ed10911f8c61d95af7c110aa583c1c04b7bec9a21b251229181f22efcd32 |
| index.html | b449d3aacfbc60524732a9504b7b33bf5ca81fa1b18c81933ee3b68bc60e27a6 |
| assets/index-BLXs-VVb.js | 0ec553c17a42beaff94f4e1c375424f50febc8306a8c0eef560a7ab431638e54 |
| assets/index-Co-slLyj.css | a572e339b7523058c3ab4011239a44c56effb2965369185d789262651a2a4444 |
| /tmp/nai-viewer-cache-build.py | 402dc7d63b570de5d7864c59e18647297352c0556c5163d62177f8b156410777 |
| /tmp/nai-viewer-cache-publish.py | eabce0fd78f08e39d6dccc1a3635d2997dfe0136dfedca80fe646289e859f7f8 |

## Operator Behavior

Refresh once to load the new frontend. The open saved viewer retains recently
seen PNGs with LRU limits of 32 entries and 64 MiB of compressed Blob bytes.
Within those limits and the original expiry, revisiting skips PNG downloads;
metadata is still authenticated/refreshed on each navigation. Close, another
selection, reload or logout clears the cache. Oversized single images display
transiently. Server-private image retention remains seven days. Broader task
stays in_progress for outstanding real-provider and interaction acceptance.
