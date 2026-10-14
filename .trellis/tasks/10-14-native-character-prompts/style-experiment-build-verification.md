# Style Experiment: Clean Production Build

- Date: 2026-10-14.
- Independent source review and ESLint/TypeScript passed; see
  `style-experiment-verification.md`.
- Production build passed in fresh stage
  `/tmp/nai-style-experiment-web-jyw7npya`.

## Inputs and Environment

Only package.json, package-lock.json, index.html, tsconfig.json,
vite.config.ts and src were copied. No `.env*` file entered the stage.
The process environment was cleared, retaining normal PATH/HOME and explicit
build/npm settings. User/global npm configuration used two distinct empty
files. Every locked dependency archive had an HTTPS URL and integrity hash;
the locked install used `npm ci --offline` with an HTTPS registry setting.

`NAI_WEB_BASE_PATH=/novelai/ npm run build` passed TypeScript and Vite.
All 14 staged input files matched the reviewed working source after build.
The input-map SHA-256 is
`cfcde8b713621600a37805f5c91c2476a8ceb09ae71a2e6681e7c66562c266a2`.
Publication must compare this same map against the work commit before
installing dist; record that result in the deployment note.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `9ae5b7191946d602d517e56db2cf230320d08d92f7915fd06bd12814ddaa5aea` |
| assets/index-DLq3cXrG.js | `c9fa12c0985b74fd17440ef5a1cf7b500fe65efa865ea36da018219394fd1791` |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |

No frontend tests, browser automation, paid image/advice calls, credential
changes or production actions were part of this build. Desktop/mobile,
keyboard and real-provider acceptance remain pending.
