# Private Images and Background Experiments: Production Release

- Published: 2026-10-15T14:05:20.643177+00:00 (2026-10-15 22:05 Asia/Shanghai).
- Source commit: 326d8f9be3a899461b31027d8a7e177902a2ed8d
- URL: https://www.firesoul.cn/novelai/
- Paired API/web release: 20261015T140424
- API: /srv/novelai/releases/20261015T140424
- Web: /srv/www/novelai/releases/20261015T140424
- API PID: 3184888

## Verified Publication

- All 23 API source/manifest/lock files equal the source commit and working bytes.
- All 19 web source/config/lock inputs equal the independently reviewed fresh env-free build.
- Staged full OpenAPI equals the committed snapshot without creating DB/image state.
- Disposable staged migration3, readiness and SQLite JSON capability probe passed.
- Locked offline Python/npm installation and pinned codex-cli 0.152.1 probe passed.
- Existing API/web pointer and PID remained unchanged throughout staging.
- Zero active jobs/runs before stop and zero active jobs after graceful shutdown.
- Verified private online v2 backup via old service-user CLI; root-owned directory0700 and DB0600, copied hash/integrity verified.
- Backup directory: /var/backups/novelai/20261015T140424-image-retention
- API stopped, staged CLI migrated schema2 to3, integrity and existing auth/history counts preserved.
- New API started before web; exact loaded OpenAPI/readiness, process working directory and private image-store ownership/mode0700 passed.
- API environment file and configured old/new process values were byte-compared in memory and unchanged. No credentials were printed/copied into this record.
- Public HTML, JS and CSS hashes match staged bytes; public readiness and neighboring /aiqq/health passed.
- Both previous releases and their public immutable assets remain available. Schema3 requires retaining the new API on web fallback; no live DB restore occurred.
- Unauthenticated new run-active/saved-experiment GETs return401/unauthenticated with no-store through the public proxy.
- No provider generation/advice was called as a release check; no env, unit, Nginx or credential edits.

## Exact Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| API source map | f8052525a4720f5eaf87371ea9ae3b62957a878bf457a7ea736400312b962b40 |
| OpenAPI snapshot | b4f708fccadbcf49c4b3cdde7d15e3fed7497c3c9b91302feda5d533876487d7 |
| Web input map | 28b6587477804fd729a78cadb582509d28e14452874e323c4647bb47db14ce99 |
| index.html | 599a8940451a4612e538223afcbab2efd192ea0222d504c6d126da07554aa441 |
| assets/index-Co-slLyj.css | a572e339b7523058c3ab4011239a44c56effb2965369185d789262651a2a4444 |
| assets/index-BBWoJo5W.js | f28e7868fd02b39fb7424b51985698aa8f931f7fa221703942a8d091ddd3b022 |
| /tmp/nai-image-retention-build.py | c18715af121170fb7e2e7da9dc7bd069584edadc225d93b6edff7d95143fb033 |
| /tmp/nai-image-retention-stage.py | 65a351931f35ce1b4d2589e89c1dba0b662605baf415f56a6a05e8c98789edb7 |
| /tmp/nai-image-retention-activate.py | 5aee1c43c4797e00794529abd6ad7772ef6f7e912ae8e8e264dc3ac13c6bef99 |

## State and Remaining Acceptance

New images are private for seven days under /var/lib/novelai/generation-images/.
SQLite contains prompts, settings, run definitions/cursors/counters and seeds,
not PNG bytes; images need their own private backup. Previous transient/expired
images cannot be reconstructed. Browser close/logout only detaches observation;
the server continues distinct combinations after failures until Stop/completion.

Quality gate: 356 offline tests plus Ruff/frozen/lock/OpenAPI and frontend
ESLint/TypeScript/source checks. No frontend/helper/browser automated tests.
Real provider output, desktop/mobile interaction and long-running operator
acceptance remain separate; the broader task stays in_progress.
