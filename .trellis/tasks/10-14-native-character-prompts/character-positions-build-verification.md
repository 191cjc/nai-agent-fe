# Character Positions Build Verification

- Fresh explicit-input stage: `/tmp/nai-character-position-web-o2jgkrom`.
- No .env files; clean build environment and distinct empty npm configs.
- HTTPS/integrity-locked `npm ci --offline`: pass.
- `NAI_WEB_BASE_PATH=/novelai/ npm run build` (TypeScript + Vite): pass.
- All 15 staged source inputs match independently reviewed working source.
- Input-map SHA-256: `d858a87900ec88366fda9381a7772fcbe19684fcc67f2842a95abc4009dd2c7f`.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-C6LuZHs6.js | `5d1843c99380b12b83acc848c5a64054eaa8efd55bb7fa5bab24cacf13cfb54a` |
| assets/index-_JAKkl6U.css | `355df73cb24a7dfa94b726052566f10ea81938dcaac5056151550b9ccbf9be79` |
| index.html | `39b52605d3617ad7d821b49d67780e243295d9dbddd989f206b194bf4654fac2` |

Paired API/web staging must compare these inputs against the work commit.
Independent read-only review found no blockers in the prepared build/staging/
activation scripts: service-user online backup, private verified snapshot,
active-job guards, unchanged configuration, API readiness/exact OpenAPI before
web, immutable retained assets and API-preserving web fallback.

No frontend/helper automated tests, browser automation or paid calls ran.
Static build/source review does not establish interactive acceptance.
