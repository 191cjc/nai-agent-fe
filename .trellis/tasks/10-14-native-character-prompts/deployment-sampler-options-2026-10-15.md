# Production Deployment: Sampler Choices

- URL: <https://www.firesoul.cn/novelai/>.
- Source: `8994c3dd050ee2edc4e40306d989bbcec5a11981`.
- Web release: `/srv/www/novelai/releases/20261015T075433`.
- Previous web retained: `/srv/www/novelai/releases/20261015T073652`.
- API unchanged: `/srv/novelai/releases/20261014T085902`, PID `2754998`, active.

Generation settings now provide seven pinned-source sampler names/IDs through
a visible dropdown and an explicit manual-ID mode. Blank drafts, manual
typing and arbitrary historical values are preserved. No model-dependent
compatibility matrix, new default or API enum was introduced.

Independent follow-up review, ESLint/TypeScript, context validation and diff
checks passed. See `sampler-options-verification.md` and
`research/sampler-options.md`. A fresh explicit-input, env-free production
build used distinct empty npm configs, HTTPS/integrity-verified locked archives
and offline install. All 14 staged inputs matched reviewed working source and
the published work commit before installation. Input-map SHA-256:
`c8395ec6e5555f5feb03ce978edc4675ed9f144ab57fa969ff0574ef76eebb85`.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `7f804a714cffb2f046b30ec0182a90694ee5d11f894468cb58138c0d07ebae59` |
| assets/index-BH0eaIgH.js | `d24ca64a69db248dadfdbe15dd825e7797d5d4d208cabaccfdd6a1449a917227` |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |

Only dist files were published, root-owned, directories 0755/files 0644.
Shared assets passed HTTP/hash checks before the atomic web switch. The
public page and its exact JS/CSS references then matched their hashes with
HTTP 200. API readiness returned `status=ok`, `/aiqq/health` returned 200,
and prior assets retained their hashes. Previous releases/assets remain;
rollback can restore the old web pointer with the existing API unchanged.

No API restart, migration, Nginx/configuration edit, credential change, direct
database access, paid call, frontend/helper test or browser automation was
performed. Interactive/provider acceptance remains pending; keep the broader
task in progress.
