# Web deployment — 2026-10-14

The operator requested deployment for manual testing. The web-only release
is live at <https://www.firesoul.cn/novelai/>. The broader deployment task
remains open for its outstanding provider, backup/restore and manual
acceptance gates.

## Release

- Source revision: `c63d64cf1836f2eff221bc596119135e70f409f9`
- Source branch: `fix/web-interaction-polish`
- Web release: `/srv/www/novelai/releases/20261014T082041`
- Active pointer: `/srv/www/novelai/current`
- Retained rollback release: `/srv/www/novelai/releases/20261008T025018`
- API release: `/srv/novelai/releases/20260924T091327` (unchanged)
- API service: `novelai-api`, active; PID `1277439` remained unchanged.

The committed web inputs were extracted into a fresh stage without `.env*`
files. A sanitized build environment used the locked offline install
(`npm ci --offline --no-audit --no-fund`) and
`NAI_WEB_BASE_PATH=/novelai/ npm run build`; both passed. The staged source
digest matched the reviewed build:
`5fe5c26aa7c21ab906f508ac97f356915aea509ae6d7ce574657612f47925980`.

The root-owned release uses directories mode `0755` and files mode `0644`.
New hashed assets were published and fetched successfully before atomically
switching only the web pointer. Existing assets and the previous release
were retained. No API restart, schema migration, Nginx configuration change
or reload was performed.

## Verification after the switch

Public HTTP requests used `Cache-Control: no-cache` and
`Accept-Encoding: identity`.

| Path | Result |
| --- | --- |
| `/novelai/` | HTTP 200; SHA-256 matches the new build |
| `/novelai/assets/index-sjcNMmKF.js` | HTTP 200; SHA-256 matches the new build |
| `/novelai/assets/index-CByBY-G2.css` | HTTP 200; SHA-256 matches the new build |
| `/novelai/api/health/ready` | HTTP 200 |
| `/aiqq/health` | HTTP 200 |
| `/novelai/assets/index-CVFHron1.js` | HTTP 200; previous asset remains available |

Published build digests:

| File | SHA-256 |
| --- | --- |
| `index.html` | `354bebd3217387f614a13e44fc34f20c51919bfd703642fd8ac4a8945a106ca9` |
| `assets/index-sjcNMmKF.js` | `3a7f77116cf51f6e82c2fb05b8b7d03504fde6277c4379b33a9d05789d94da98` |
| `assets/index-CByBY-G2.css` | `8ec31022d634d8bfeaa0d4438d1ae36d245b557d06b2694ddace39f8310cd310` |

The active web pointer resolves to the new release. The API pointer and
process PID match their pre-deployment values. All post-switch checks passed;
rollback was not needed. If rollback is required, atomically restore only
the web pointer to the retained previous release using the procedure in
`deploy/README.md`, then repeat the page, asset and health checks.

## Manual testing scope

The interface and existing parameter history are available for operator
testing. Production NovelAI and Codex credentials remain unset, so image
generation and AI advice remain disabled. No paid provider calls,
credential changes, frontend automated tests or browser automation were
performed. Interactive desktop/mobile acceptance remains pending.
