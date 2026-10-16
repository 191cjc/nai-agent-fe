# Canvas Layout: Final Fresh Build

- Independent affected frontend gate: GREEN; see check-canvas-layout.md.
- Final stage: /tmp/nai-canvas-layout-web-8xto3sxj
- Report: /tmp/nai-canvas-layout-web-8xto3sxj/build-report.json
- All19 explicit manifest/config/lock/src inputs match working source and the
  independent final four-file freeze. No new dependency or source files.
- Fresh explicit five root inputs plus src, no .env files, empty independent
  npm configuration, clean process environment and HTTPS/integrity lock checks;
  npm ci --offline followed by build with NAI_WEB_BASE_PATH=/novelai/ passed
  TypeScript and Vite. npm's esbuild install-script approval warning required
  no configuration/approval change; the build completed successfully.
- Preliminary stages /tmp/nai-canvas-layout-web-vv0cy3i4 and
  /tmp/nai-canvas-layout-web-y2uz016x passed compilation but are superseded by
  the final independent CSS fixes, including very short scroll-region bounds.
  Their publication pointers were removed; only the final stage/report above
  is eligible for publication.
- No frontend/helper/browser tests or paid calls. No backend/API/schema change.

| Artifact | SHA-256 |
| --- | --- |
| Web input map | 09dd9835ed9ce2ee2187e0b16e90d5dad8868cb40350e4c63b8ae5f806f12af2 |
| index.html | 8ffa49c08b52abbac969bc3b6f26ef44dc027610a638f891b14c06729a2b29cc |
| assets/index-C_wPKPe_.js | 8750dde8e781976afa5c78c825b687931d685bfed894faadea552694df85b840 |
| assets/index-C09sxZFi.css | 92ca4dc454aa8eaa0005cdfbc3795eb4bdd830dbde727561ea2f242560fde277 |
| /tmp/nai-canvas-layout-build.py | 6b143a582dbb30af1837b5b4f3fa57cffb76285d1addcca2d2791cc333cb8407 |
| /tmp/nai-canvas-layout-publish.py | fa19398e6e303c11d05df13dc7b2668dbd5df67896c2359a472a18d42ed9d2e1 |

Baseline captured from public bytes/live service on2026-10-16T02:27:02Z:
web20261015T145554; API20261015T140424, PID3184888. Only web is published after
the source commit. Check exact public assets/health/old assets and unchanged
API state; desktop/mobile visual interaction remains operator acceptance.
