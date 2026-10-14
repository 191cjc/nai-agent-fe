# Production Deployment: Prompt Tags and Weights

## Release

- URL: <https://www.firesoul.cn/novelai/>
- Source: `0d12ea3d8f7ed74d0ca71f4668ab13199247a3d8`
- Web release: `/srv/www/novelai/releases/20261014T093928`
- Previous web retained: `/srv/www/novelai/releases/20261014T085902`
- API remains `/srv/novelai/releases/20261014T085902`, PID `2754998`, active.

## Quality and Build

Implementation and independent full-scope source review passed ESLint and
TypeScript. The review fixed blur-induced layout movement and the ambiguous
trailing-colon emphasis boundary. See `prompt-weight-verification.md`.
Trellis context validation and `git diff --check` passed.

A fresh temporary directory received only package.json, package-lock.json,
index.html, tsconfig.json, vite.config.ts and src. No `.env*` was included.
The locked install ran offline in a clean environment, retaining normal HOME
and setting distinct empty npm user/global config files and an HTTPS registry.
All locked package archives had HTTPS resolved URLs and integrity hashes.
`npm run build` passed with `NAI_WEB_BASE_PATH=/novelai/`.

The staged input map matched both reviewed working files and committed source:
SHA-256 `b9fd55969666fe254073733bcd1e51b026b97b32afcd715b1085cef48a65156c`.
Only dist files were published, root-owned, with directories 0755/files 0644.
New immutable assets were published and verified before the atomic web switch.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `20b1514ec1715fafe25d7414b712c89d8a7e7c85924448ddc8f531f86692054d` |
| assets/index-B9OVJLZY.js | `52895b686215bc0842a3a3d668fcaa43e104cb9dfcd5da5589d130d776a2e473` |
| assets/index-fJDPsUEp.css | `97fcc389df1c2a1e476d4df0c9eaeb2b2d0f620b0499fe2a97fb41c6f1aef9a6` |

## Public Checks and Rollback

All checks returned HTTP 200: `/novelai/`, its exact referenced JS/CSS,
`/novelai/api/health/ready`, `/aiqq/health`, and the prior web release's JS/CSS.
Page/assets matched their local SHA-256 values using no-cache and identity
encoding headers. The active web pointer resolves to the new release; API
pointer/PID are unchanged. No API restart, migration, Nginx/configuration edit,
credential change, database access or paid call was performed.

Rollback for this frontend-only change can atomically restore the previous
web pointer while leaving the active native-capable API in place. All previous
assets/releases were retained; no rollback was needed.

No frontend automated tests or browser automation ran. Desktop/mobile and
keyboard interaction still need operator acceptance, and no real provider
output or live history round trip is claimed. Keep the active task open for
that acceptance.
