# Production Deployment: Style Weight Experiment

## Release

- URL: <https://www.firesoul.cn/novelai/>
- Source: `5e3795fd64ade0bbe9b7afb7f8f2c5bc02301e29`.
- Web release: `/srv/www/novelai/releases/20261014T101427`.
- Previous web retained: `/srv/www/novelai/releases/20261014T093928`.
- API remains `/srv/novelai/releases/20261014T085902`, PID `2754998`, active.

## Delivered Behavior

The style-heading experiment control selects independent tag occurrences and
decimal min/max/step ranges. Exact lazy Cartesian enumeration preserves every
combination, with the last selected source occurrence varying fastest.
The preview shows group count and total requested images. All generation
settings and character children are captured at Start. A supplied seed is
reused; otherwise only the first request is random and the first observed
effective seed is reused thereafter, without changing the editable draft.

Only one group is submitted at a time, with images fetched and archived before
the next POST. Stop prevents subsequent groups; errors halt without paid
retries. Accepted work can be explicitly rechecked without resuming the halted
sequence. Comparisons retain labeled images in current-page memory and render
six groups per page with download links. Refresh does not restore the run;
ordinary task parameter history remains durable.

## Quality and Build

Independent full-scope source review found no concrete defects. ESLint,
TypeScript, task context validation and `git diff --check` passed. See
`style-experiment-verification.md` and
`style-experiment-build-verification.md` for detailed evidence.

The production build used a fresh directory with only the explicit frontend
inputs and no `.env*` files. The process environment was cleared, keeping
normal PATH/HOME, distinct empty user/global npm configuration files and an
HTTPS registry setting. All dependency archives had HTTPS URLs and integrity
hashes; the locked install ran offline.

All 14 staged input files matched both the reviewed working source and the
published work commit before publication. Input-map SHA-256:
`cfcde8b713621600a37805f5c91c2476a8ceb09ae71a2e6681e7c66562c266a2`.
Only dist files were installed, root-owned, directories 0755/files 0644.
New immutable shared assets were published and HTTP/hash-verified before the
atomic web pointer switch.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `9ae5b7191946d602d517e56db2cf230320d08d92f7915fd06bd12814ddaa5aea` |
| assets/index-DLq3cXrG.js | `c9fa12c0985b74fd17440ef5a1cf7b500fe65efa865ea36da018219394fd1791` |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |

## Public Checks and Rollback

HTTP 200 and exact SHA-256 checks passed for `/novelai/` and the JS/CSS
actually referenced by its HTML, using no-cache and identity-encoding
headers. `/novelai/api/health/ready` returned its expected `status=ok` and
`/aiqq/health` returned HTTP 200. The previous web release's JS/CSS remain
available with their original hashes.

The active web pointer resolves to the new release. The API pointer/PID are
unchanged. No API restart, migration, Nginx/configuration edit, credential
change, direct database access, paid call, frontend automated test or browser
automation was performed. All previous releases/assets were retained.
Rollback can atomically restore the previous web pointer while preserving
the active API; no rollback was required.

Operator desktop/mobile/keyboard interaction, live history round trips and
actual-provider output remain pending. Keep the task in progress for this
acceptance; static checks and public HTTP checks do not establish provider
generation success.
