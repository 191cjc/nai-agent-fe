# Production Deployment: Submission Refusal and Image Provider

- URL: <https://www.firesoul.cn/novelai/>.
- Completed: `2026-10-15T08:33:23.144080+00:00`.
- Work commit: `be99b7d023b6c01516ebae1105f48eaf6a7aea3c`.
- API and web release ID: `20261015T082138`.
- API: `/srv/novelai/releases/20261015T082138`, active PID `3098684`.
- Web: `/srv/www/novelai/releases/20261015T082138`.
- Previous API retained: `/srv/novelai/releases/20261014T085902`.
- Previous web retained: `/srv/www/novelai/releases/20261015T075433`.
- Private verified backup directory: `/var/backups/novelai/20261015T082138-enable-images`.

## Root Cause and Fix

The existing API process had no NovelAI provider configuration, causing the
reported generation submissions to return 503 before doing work. The browser
classified every 5xx as outcome-uncertain. Independent review also found that
the route caught all RuntimeErrors, including history/executor errors after
persistence or enqueue, under the same refusal code.

The backend now raises/catches only GenerationNotConfigured at the initial
missing-executor guard. Only that exact POST refusal is classified as definite
by the browser, with a not-configured message and no acknowledgement lock.
Other unknown transport/server outcomes retain their lock; experiments halt
and neither case automatically retries. Accepted-job provider errors retain
their existing separate behavior.

## Authorization and Provider Enablement

The operator explicitly selected `授权接入现有配置并上线（推荐）` after the
reviewable release and enablement plan were prepared. Under that authorization,
only the existing private project's NAI_NOVELAI_MCP_URL and
NAI_NOVELAI_MCP_TOKEN were copied to /etc/novelai/api.env. Unrelated settings,
including Codex advice, were preserved bytewise apart from line separation and
verified by parsed values and the new process's environment. No secret was
printed, placed in argv, committed or included in web assets.

Only initialize, notifications/initialized and tools/list were called. The
MCP protocol, generation fields and native independent-character schema
passed. No tools/call, generation or advice request was made. Provider
configuration loaded by the actual new API process was verified without
printing values. This enables user testing; it does not prove paid output.

## Quality, Backup and Switch

The combined independent quality gate passed: **215 offline backend tests**,
Ruff, frozen dependency/lock checks, frontend ESLint/TypeScript, unchanged
OpenAPI snapshot and a fresh explicit-input env-free web build. See the linked
task verification records and `submission-refusal-release-preparation.md` for
source/artifact hashes. All staged API/web inputs matched work commit
`be99b7d023b6c01516ebae1105f48eaf6a7aea3c` before activation.

The activation script received focused independent source review. An env
write/recovery temporary-file issue was corrected before execution; the final
reviewed script SHA-256 was
`3715def0d9dc70fbf4168667b341996dbf8edffaa97f731f9b1be72039584dc6`.
Only safe phase labels, booleans and public artifact hashes were emitted.

There were zero queued/running jobs before restart. Live database reads and
the documented online-backup CLI ran as novelai to preserve WAL/SHM ownership.
The private database snapshot passed integrity_check. Backup directory mode
is 0700/root-owned; the snapshot and original environment are 0600/root-owned.
The updated operator environment was atomically installed with mode 0600.

The service was stopped gracefully, API pointer switched atomically and the
new API started before publishing the web. Database schema remains version
2; the existing pre-start migration was unchanged.
The API PID changed from `2754998` to `3098684`.
Shared immutable assets passed HTTP/hash checks before the atomic web switch.
No Nginx/unit edit, database restore or old release/asset pruning occurred.

## Public and Final Checks

| Artifact | SHA-256 |
| --- | --- |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |
| assets/index-rFLLAA7s.js | `43bf2d078e5b42d70e662ac6db4b9844a4da7abf5faf01c6d345a05cf23396fc` |
| index.html | `56ad6b8adacbbceb23599ae634b7aedadd757eb509f92c3b0686546f9312353c` |

The public page and its actual JS/CSS references matched these hashes with
HTTP 200. Public database readiness returned status=ok, /aiqq/health passed,
and previous asset hashes remained accessible. Final pointer/PID checks
passed. Independent post-deployment metadata checks confirmed private backup
and environment permissions, novelai ownership/mode 0600 for the live SQLite
and any present WAL/SHM files, and the reviewed activation-script hash.

## Rollback and Remaining Acceptance

No rollback was required. Retain the corrected API after this frontend has
been published, even when reverting web/configuration: already-open tabs may
keep the new classification, incompatible with the old broad RuntimeError
catch. Prefer a forward fix; keep active jobs in mind before any further
restart. Do not automatically retry paid work or restore the database merely
to revert these code/configuration changes.

No frontend/helper automated test, browser automation or paid provider probe
was run. Actual image output and desktop/mobile acceptance remain for the
operator. The broader native-character task remains in progress.
