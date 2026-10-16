# Automatic Character Position: Production Release

- Published: 2026-10-16T06:08:18.787292+00:00 (Asia/Shanghai: 2026-10-16 14:08:18 CST).
- Source commit: 7c7e3d7bea23c49fb10d79a6bcb9d330a76806f0
- URL: https://www.firesoul.cn/novelai/
- Matched API/web release: 20261016T060747
- API: /srv/novelai/releases/20261016T060747
- Web: /srv/www/novelai/releases/20261016T060747
- API PID: 3427318

## Authorization and Behavior

The user initially prohibited restart, then explicitly authorized it with
"现在可以重启服务" and later requested continuation. The external documentation
path was ignored. Fresh non-billable discovery against the configured MCP
had confirmed the new nullable boolean flag before implementation.

The global character-position selector defaults to manual for compatibility.
Automatic mode retains draft/saved coordinates while sending true and no
child x/y to MCP. Manual mode restores draggable positioning and sends exact
axes, plus false when supported. History, entry restore, reuse and frozen
experiments preserve mode; old definitions/history remain manual without
rewriting raw definitions. Unsupported automatic capability fails before
paid tools/call, with a clear actionable error.

## Verified Publication

- All 23 API manifest/lock/source inputs equal committed and working source.
- All 19 web source/config/lock inputs equal the final fresh env-free build, including the independently corrected automatic/manual character hint.
- Pinned frozen offline Python/npm installs and service-user codex-cli 0.152.1 passed.
- Staged OpenAPI exactly matches the additive reviewed snapshot and creates no DB/image state; disposable schema3 migration/readiness/SQLite JSON probes passed.
- API/web pointers and old PID stayed unchanged throughout preparation/staging.
- Verified zero active jobs/runs before restart and zero active work after graceful shutdown; no generation or experiment was interrupted.
- Private online schema3 backup verified at /var/backups/novelai/20261016T060747-auto-character (root directory0700/database0600, matching copy hash and SQLite integrity).
- Schema stayed3; same-version migration/readiness preserved existing auth/history/run record counts.
- API started and passed readiness/exact running OpenAPI before web publication. New process cwd and private image-root ownership/mode0700 passed.
- Existing API env file and old/new configured process values were compared privately in memory and remained unchanged; no secrets were printed or written to release records.
- Exact public HTML/JS/CSS hashes, public API readiness, retained previous immutable assets and neighboring /aiqq/health passed.
- Unauthenticated run-active/saved-experiment GETs return401/unauthenticated with no-store.
- No unit, Nginx, provider or credential changes; retained private images remain in place.
- No paid generation/advice release probe, frontend/helper automated test or browser automation.

## Artifact Identity

| Artifact | SHA-256 |
| --- | --- |
| API source map | d5ef4c1d4c3dcbdb606a6649fedddeb181c93ac9bab2d4fcecc7eed568b77960 |
| OpenAPI snapshot | db0f0b60bec24c63b48078a34e4ea9bc26a1610a42ff578fcc07165acec2bb1c |
| Web input map | 2bc64a69c944ecafadd48cdf89764eb3b30633d158c05bae7ae505e33b78a70e |
| assets/index-Bjw-xnGE.js | 25f2899500c7bf1757ea1b530b8a8fe69b645a0d6d4f75c809dc3e8599a7dd45 |
| assets/index-C3k99DW-.css | 1b7f9021a3989a7c4b314ed66615635348da71b8d88e79d7f12285c27160cafa |
| index.html | 53721d7a22725ea599fe74f2661d188c23868e4dc631fb8a81ea9a8c51a5d559 |

## Recovery and Acceptance

Previous API/web releases and immutable assets remain available. Retain this
compatible API on web fallback for already-open tabs or accepted automatic
mode snapshots; older schema3 APIs ignore the mode and send manual axes.
Never restore the live DB. Pre-validation helper recovery checks for auto
job/run snapshots before selecting the baseline API.

Independent full gate:462 offline backend tests, Ruff/frozen sync/lock,
reviewed additive OpenAPI and web ESLint/TypeScript/source review. The final
explicit19-input clean build was repeated after the checker hint fix. See
check-auto-character-position.md and auto-character-position-build-verification.md.
Actual generated placement appearance and desktop/mobile interaction remain
operator acceptance; the broader task stays in_progress.
