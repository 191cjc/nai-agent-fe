# Prepared Release: Submission Refusal

Status: **staged, not activated**. Production provider configuration and the
combined switch/restart await explicit authorization. No secret was read.

- Work commit: `be99b7d023b6c01516ebae1105f48eaf6a7aea3c`.
- Prepared API: `/srv/novelai/releases/20261015T082138`.
- Prepared web: `/srv/www/novelai/releases/20261015T082138`.
- Active API retained: `/srv/novelai/releases/20261014T085902`, PID `2754998`.
- Active web retained: `/srv/www/novelai/releases/20261015T075433`.
- URL: <https://www.firesoul.cn/novelai/>.

## Verified Preparation

The independent combined quality gate passed: 215 offline backend tests,
Ruff, frozen sync/lock consistency, frontend ESLint/TypeScript, OpenAPI
snapshot and diff checks. The fresh env-free web build passed; see
`check-submission-refusal.md`, `backend-submission-refusal-verification.md`
and `submission-refusal-build-verification.md`.

Every staged API source/lock input came from the work commit and matched
working source. Only the four API manifest/lockfiles and src were staged.
Package archive URLs were HTTPS with npm integrity hashes. Frozen offline
Python sync and offline npm production install used a cleared environment,
normal PATH/HOME, distinct empty npm configs and no UV config/env files.
The API release is root-owned and readable by the service user. Running as
that user, the pinned CLI version probe returned `codex-cli 0.152.1`
and a provider-free OpenAPI import did not create a database.

API source-map SHA-256:
`d4fcd1a5ce4e93a179320b152b03adfa9f43fbfd152f5aa0128d6ec0f846d830`.

All 14 clean web inputs matched the same work commit. Only dist files were
installed in the inactive versioned web directory, root-owned, directories
0755/files 0644. Web source-map SHA-256:
`d91516a26a15638c8280856f2e6982acbc87ea9622a312df908498e4769d19cd`.

| Staged web artifact | SHA-256 |
| --- | --- |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |
| assets/index-rFLLAA7s.js | `43bf2d078e5b42d70e662ac6db4b9844a4da7abf5faf01c6d345a05cf23396fc` |
| index.html | `56ad6b8adacbbceb23599ae634b7aedadd757eb509f92c3b0686546f9312353c` |

Staging verified that both active pointers and the API PID remained unchanged.
The public page, database readiness and /aiqq/health passed HTTP 200 before
staging; both active hashed assets retained their expected SHA-256. These
checks do not establish provider configuration or paid image output.

## Activation Still Required

Follow `production-image-enable-plan.md`: authorize the two-key NovelAI
configuration change, validate only non-billable MCP discovery, check active
jobs, take private verified backups, activate the API before the web and
verify public hashes/health. After the new web is published, retain the
corrected API even when reverting web/config, because open tabs can keep the
new submission classification. No schema/request/lock change is involved.

No shared asset publication, pointer switch, service restart, database
mutation, production environment edit, credential read, paid generation/advice
request or frontend/helper/browser automated test occurred in preparation.
The broader task remains in progress pending activation and operator testing.
