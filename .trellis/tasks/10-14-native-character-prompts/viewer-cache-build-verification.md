# Viewer Cache: Fresh Build Verification

- Independent cache/source/static gate: GREEN; see check-viewer-cache.md.
- Fresh stage: /tmp/nai-viewer-cache-web-5f_6vbd5
- Report: /tmp/nai-viewer-cache-web-5f_6vbd5/build-report.json
- Clean copy includes five explicit config/manifest/lock inputs and all src
  files; all 19 input hashes match working source and the independently frozen
  saved-results.ts. No .env files were copied.
- Empty independent npm configuration, clean process environment, HTTPS and
  integrity-verified lock entries, npm ci --offline, then build with only
  NAI_WEB_BASE_PATH=/novelai/ added. TypeScript and Vite build passed.
- npm emitted its install-script approval warning for esbuild; no approval or
  configuration mutation was performed, and the production build succeeded.
- No frontend/helper/browser tests or paid calls. No API/schema/config change.

| Artifact | SHA-256 |
| --- | --- |
| Web input map | 3df4ed10911f8c61d95af7c110aa583c1c04b7bec9a21b251229181f22efcd32 |
| index.html | b449d3aacfbc60524732a9504b7b33bf5ca81fa1b18c81933ee3b68bc60e27a6 |
| assets/index-BLXs-VVb.js | 0ec553c17a42beaff94f4e1c375424f50febc8306a8c0eef560a7ab431638e54 |
| assets/index-Co-slLyj.css | a572e339b7523058c3ab4011239a44c56effb2965369185d789262651a2a4444 |
| /tmp/nai-viewer-cache-build.py | 402dc7d63b570de5d7864c59e18647297352c0556c5163d62177f8b156410777 |
| /tmp/nai-viewer-cache-publish.py | eabce0fd78f08e39d6dccc1a3635d2997dfe0136dfedca80fe646289e859f7f8 |

Publication baseline was re-read from the public site and live service:
web/API release 20261015T140424, API PID3184888; previous HTML/JS/CSS hashes
match deployment-retention-and-background-2026-10-15.md. Publish only the web
after the source commit; preserve live API and background experiments.
