# Experiment Zero Weight: Production Release

- Published: 2026-10-16T04:06:17.932344+00:00 (Asia/Shanghai:2026-10-16 12:06).
- Source commit: 65560f3318a35b07e56ad766ce77c36062d5b9b8
- URL: https://www.firesoul.cn/novelai/
- Matched API/web release: 20261016T034213
- API: /srv/novelai/releases/20261016T034213
- Web: /srv/www/novelai/releases/20261016T034213
- API PID: 3388714

## Verified Publication

- All23 API manifest/lock/source files equal the committed and working inputs.
- All19 web source/config/lock inputs equal the fresh env-free locked build.
- Staged service-user OpenAPI creates no DB/image state and exactly equals the unchanged snapshot.
- Disposable staged schema3/migration/readiness/SQLite JSON and pinned codex-cli0.152.1 probes passed.
- First activation preflight observed an active48-group experiment and left the service unchanged. Waited for natural completion; all48 groups succeeded with its original version1 definition before release. No Stop or interrupted paid work.
- Verified zero active jobs/runs before stop and zero active jobs after graceful shutdown.
- Verified private online schema3 backup: /var/backups/novelai/20261016T034213-zero-weight; root directory0700/database0600 with copied hash and SQLite integrity checks.
- Schema stayed3; same-version migration/readiness preserved auth/history/run record counts.
- API started before web; exact running OpenAPI, process working directory and private image-root ownership/mode0700 passed.
- Existing API env file and configured old/new process values were compared in memory and unchanged. No credentials were printed in release records.
- Exact public HTML/JS/CSS hashes, readiness, neighboring /aiqq/health and retained old immutable assets passed.
- Public unauthenticated run-active/saved-experiment GETs return401/unauthenticated and no-store.
- No env, unit, Nginx, provider or credential changes. No paid generation/advice release probes.

## Artifact Identity

| Artifact | SHA-256 |
| --- | --- |
| API source map | 1ef11bdd9a2d0642dd8c8e0c7b093f441cedad092d899553eeae09d8a9ecfb99 |
| OpenAPI snapshot | b4f708fccadbcf49c4b3cdde7d15e3fed7497c3c9b91302feda5d533876487d7 |
| Web input map | 3d2ddd81aa8d89f68409689ca70eed6f7d21a50f65f8a6e03d0c66c7df227be4 |
| index.html | f3d483916c6b19ec71997d73406c31708312a2d6d9049f38fdf511c4d954ede8 |
| assets/index-C09sxZFi.css | 92ca4dc454aa8eaa0005cdfbc3795eb4bdd830dbde727561ea2f242560fde277 |
| assets/index-C8NScD9n.js | 0db58a4cc43afb3ac243bdac3c792cd697405bffd5276c6018348343f2c1cd3e |

## State and Acceptance

New experiments persist internal version2. Exact zero omits the selected
occurrence while retaining its label/index/0.0 comparison metadata. All-empty
style requires shared prompt content at preflight. New definitions require
keeping the compatible API on web fallback; old schema3 API is unsafe after
v2 acceptance. Never restore the live database. Previous releases are retained.

Independent gate:385 offline backend tests plus Ruff/frozen sync/lock/OpenAPI,
web ESLint/TypeScript/source review and fresh explicit19-input env-free build.
No frontend/helper/browser automated tests. See check-zero-weight.md and
zero-weight-build-verification.md. Real zero-omission image appearance and
operator interaction remain separate acceptance checks; the broader task stays
in_progress. Existing48-group success is not a paid probe of this new version.
