# Clean Build: Submission Refusal

Date: 2026-10-15. The production web build passed in
`/tmp/nai-submit-refusal-web-hdtwbjlz`. Inputs were only package.json,
package-lock.json, index.html, tsconfig.json, vite.config.ts and src. No
`.env*` entered the stage. The process environment was cleared except normal
PATH/HOME and explicit npm/build settings; user/global npmrc files were
distinct and empty. All dependency archives had HTTPS URLs and integrity
hashes. `npm ci --offline` followed by `NAI_WEB_BASE_PATH=/novelai/ npm run
build` passed, including TypeScript compilation.

All 14 staged input hashes matched current source and the independently
reviewed store.ts hash. Input-map SHA-256:
`d91516a26a15638c8280856f2e6982acbc87ea9622a312df908498e4769d19cd`.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `56ad6b8adacbbceb23599ae634b7aedadd757eb509f92c3b0686546f9312353c` |
| assets/index-rFLLAA7s.js | `43bf2d078e5b42d70e662ac6db4b9844a4da7abf5faf01c6d345a05cf23396fc` |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |

This is build evidence, not publication or paid image output evidence.
The backend's dedicated refusal catch must be active before switching this
web release. No frontend/helper tests, browser automation, paid calls,
credential reads or production switches were made for this build.
