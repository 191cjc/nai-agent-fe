# Experiment Zero Weight: Fresh Build Verification

## Web Artifact

- Fresh explicit stage: /tmp/nai-zero-weight-web-5jio8rt_
- Copied exactly 19 source/config/lock inputs; no .env files.
- Sanitized environment and empty npm user/global config; HTTPS/integrity-verified lock.
- npm ci --offline and NAI_WEB_BASE_PATH=/novelai/ npm run build passed.
- Source map SHA-256: 3d2ddd81aa8d89f68409689ca70eed6f7d21a50f65f8a6e03d0c66c7df227be4
- All 19 copied inputs still equal the frozen working source.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-C09sxZFi.css | 92ca4dc454aa8eaa0005cdfbc3795eb4bdd830dbde727561ea2f242560fde277 |
| assets/index-C8NScD9n.js | 0db58a4cc43afb3ac243bdac3c792cd697405bffd5276c6018348343f2c1cd3e |
| index.html | f3d483916c6b19ec71997d73406c31708312a2d6d9049f38fdf511c4d954ede8 |

## Reviewed Release Helpers

Scripts were adapted under a new prefix with a freshly captured production
baseline. Staging requires equality with the final source commit and build.
Activation requires no active jobs/runs, a verified private online schema3
backup, API-first readiness/OpenAPI/config continuity, exact public assets and
retained previous assets. Schema stays3. New v2 run definitions require keeping
the compatible API on web fallback; no live database restore.

| Helper | SHA-256 |
| --- | --- |
| /tmp/nai-zero-weight-build.py | 2741e0ffd635261b4f3e68e7402478bea8aee4e6875d5232372dc2cb3ce7214f |
| /tmp/nai-zero-weight-stage.py | 33429d4969054df1cc48c177ac56c57ee248079d73c1e211602d1642ddc22383 |
| /tmp/nai-zero-weight-activate.py | dfb86fc21c101e9c21bfd709202901bcc23cffb8dcf8db00b69ee15e6f54dc61 |

## Quality and Limits

See check-zero-weight.md for independent full affected-layer review and exact
backend/static check results. No frontend/helper/browser automated tests or
paid provider calls. Actual generated appearance and interaction remain
operator acceptance; source review/builds do not claim that acceptance.
