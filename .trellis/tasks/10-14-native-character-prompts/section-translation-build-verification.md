# Per-section AI Translation Clean Build Verification

Fresh 25-input production build in an isolated temporary directory.
Explicit root inputs plus the complete source set; no .env files, clean process
environment, HTTPS integrity-locked dependencies and offline npm ci. Base: /novelai/.

- TypeScript/Vite production build passed.
- Source map SHA-256: 6468740cc44026368e61e703d08f116831b57942c47bd1ea4234284c4ffa281f.
- assets/index-DgzvIkCf.js: cd9ed01a601edbce3c70ff58fd1763a2b0b16bc3624bc6e537ac4ef0bb89d10a
- assets/index-Domzn7er.css: 7dbc3f2685ad41673943cc079ea2b7f9c961b90913fcc2d7d913c44946983b11
- index.html: dc3f94a2321a38b5ed129d15c2c03cd8ee245ddf283eb4955434c7fe854fdf10

Publication must match the exact working, committed and build input sets and
hashes. Matched API-first publication requires an idle service, verified private
online SQLite backup, unchanged schema4/OpenAPI/configuration, preserved private
images and original expiry, retained old assets and exact public release hashes.
No frontend/helper/browser automated tests, live AI/provider requests or
authenticated private-image downloads were used. Real explanation quality and
interactive behavior remain operator acceptance.
