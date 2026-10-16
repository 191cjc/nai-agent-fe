# Canvas Layout: Production Release

- Published: 2026-10-16 02:58 UTC (10:58 Asia/Shanghai).
- Source commit: 8f86e5a830f02827e44d58b5aab85dce40374b0e
- URL: https://www.firesoul.cn/novelai/
- New web: /srv/www/novelai/releases/20261016T025802
- Previous web retained: /srv/www/novelai/releases/20261015T145554
- API unchanged: /srv/novelai/releases/20261015T140424, PID3184888.
- Deployment report: /tmp/nai-canvas-layout-deployment-report.json

## Verified Publication

- All19 final fresh build inputs match working and committed source bytes,
  including the confirmed independent final four-file freeze. Earlier builds
  superseded during source review were never published.
- Dist bytes match the final build report; installed release files/directories
  have root ownership and modes0644/0755. Immutable shared assets were collision
  checked and verified publicly before the atomic web pointer switch.
- Previous web/API pointer, API PID/active state and public HTML hash were
  checked before activation. Final public HTML and exact JS/CSS paths/hashes
  match the committed-source build.
- Public /novelai/api/health/ready reports ok; /aiqq/health and both previous
  immutable assets return200 with expected hashes. Old release remains present.
- Final web pointer is the new release; API pointer/PID/active state unchanged.
  No API restart, DB migration, config/credential/unit/Nginx changes, provider
  calls or server-experiment interruption.
- Independent full affected frontend/source/static gate and final env-free build
  passed. No frontend/helper/browser automated tests or browser work. Visual,
  desktop/mobile and real-provider interaction remain operator acceptance.

## Exact Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| Web input map | 09dd9835ed9ce2ee2187e0b16e90d5dad8868cb40350e4c63b8ae5f806f12af2 |
| index.html | 8ffa49c08b52abbac969bc3b6f26ef44dc027610a638f891b14c06729a2b29cc |
| assets/index-C_wPKPe_.js | 8750dde8e781976afa5c78c825b687931d685bfed894faadea552694df85b840 |
| assets/index-C09sxZFi.css | 92ca4dc454aa8eaa0005cdfbc3795eb4bdd830dbde727561ea2f242560fde277 |
| /tmp/nai-canvas-layout-build.py | 6b143a582dbb30af1837b5b4f3fa57cffb76285d1addcca2d2791cc333cb8407 |
| /tmp/nai-canvas-layout-publish.py | fa19398e6e303c11d05df13dc7b2668dbd5df67896c2359a472a18d42ed9d2e1 |

## Operator Behavior

Refresh once to load the canvas-centered workspace. The bottom prompt drawer
starts expanded, preserves mounted editor/configuration state when collapsed,
and frees space for the main image. Generate/settings remain at the bottom;
experiment progress/reconnect/Stop and uncertainty recovery stay outside the
prompt body. Current images use arrows/thumbnails without further downloads;
saved image arrows retain fresh metadata and bounded cache behavior. History
reuse opens prompts, resume reveals current status, and saved close preserves
left tools. Broader task stays in_progress for remaining operator acceptance.
