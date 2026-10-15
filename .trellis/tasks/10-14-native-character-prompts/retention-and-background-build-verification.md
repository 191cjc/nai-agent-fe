# Retained Images and Background Experiments: Build Verification

Fresh explicit env-free build after independent frontend source/static review.
No browser/frontend/helper automated tests or paid calls.

- Build stage: /tmp/nai-image-retention-web-cui67u71
- Base path: /novelai/
- Inputs: 19 source/config/lock files; all match current reviewed bytes.
- Combined input SHA-256: 28b6587477804fd729a78cadb582509d28e14452874e323c4647bb47db14ce99
- npm ci --offline: 179 locked packages; HTTPS/integrity preflight passed.
- npm run build: TypeScript and Vite passed; 1612 modules.
- No source .env files, inherited NAI/VITE credentials or project npmrc copied.
- npm emitted the existing esbuild postinstall allow-scripts advisory; build passed.

| Output | SHA-256 |
| --- | --- |
| assets/index-BBWoJo5W.js | f28e7868fd02b39fb7424b51985698aa8f931f7fa221703942a8d091ddd3b022 |
| assets/index-Co-slLyj.css | a572e339b7523058c3ab4011239a44c56effb2965369185d789262651a2a4444 |
| index.html | 599a8940451a4612e538223afcbab2efd192ea0222d504c6d126da07554aa441 |

Staging will additionally require every build input to match the committed
source and verify the paired API/OpenAPI before any production switch.
