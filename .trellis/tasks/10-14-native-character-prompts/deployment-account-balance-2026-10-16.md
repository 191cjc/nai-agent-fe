# Image-service Balance Deployment

## Result

Published source commit377a634 as matched API/web release20261016T090442
at 2026-10-16T09:05:10.963180+00:00 (17:05 China time).

Workspace: https://www.firesoul.cn/novelai/

The header now shows configured image-service Anlas with manual refresh and
accessible total/fixed/purchased/fetch-time details. Entry, visible30s polling
and trailing coalesced activity refresh keep the value current independently
of generation. Failed refresh retains the last known value marked unupdated
with its original timestamp. Logout/session/disposal clear protected state.
No per-request free/paid classification or advice billing claim is made.

## Verification

- Independent full affected-layer gate GREEN:639 fake-only offline backend
  tests, frozen dependencies/lock, Ruff, exact additive OpenAPI, web ESLint/
  TypeScript and source review. No product corrections were needed.
- Fresh env-free locked25-input /novelai/ build passed. Exact working/committed/
  build input sets and hashes match. API staged from the same committed sources;
  pinned adjacent CLI remains codex-cli0.152.1. Isolated schema4/readiness/JSON
  probes and side-effect-free exact OpenAPI pass.
- Initial staging stopped before writes when generated ignored egg-info files
  appeared in its source-set comparison. The helper now excludes only generated
  egg-info/cache artifacts; independent re-review passed and all runtime source
  files/new packages still require exact sets/hashes. No production change
  occurred during that rejected staging attempt.
- Private verified online schema4 backup before restart. Both immediately
  before restart and after graceful stop:zero active jobs/runs. No migration
  or live DB restore; users/tokens/sessions/jobs/runs/snapshots preserved.
- API-first running OpenAPI matches reviewed snapshot SHA-256
  `9312ec42258a35b66d20876bd56c8e46599840962ce8f6858c0d352a311c6eaa` before web activation.
- Provider configuration bytes and private process environment unchanged.
  Existing72 manifest/PNG result sets retain exact bytes and original expiry;
  all72 images verified,0 expired during release. Detailed inventory remains
  root-private outside web/source artifacts.
- Loopback and public GET /api/account/balance without a session return401,
  unauthenticated and Cache-Control:no-store. Authenticated route behavior is
  verified by fake integration tests; no live browser session/token was created.
- Separately, the deployed account adapter successfully queried get_subscription
  with the running service's existing private configuration. Strict normalized
  fields/safe sum/recent timestamp verified; no raw account values or credentials
  printed. This is adapter evidence, not a live authenticated browser-route GET.
  The probe first failed before launching because its clean PATH omitted
  runuser; using /usr/sbin/runuser fixed the helper invocation without any
  product or configuration change.
- Public HTML/JS/CSS match exact build hashes; previous assets/releases retained.
  Public API readiness and existing /aiqq/health return200.
- Paid generation/advice probes:0. No frontend/helper automated tests or browser
  automation. Desktop/mobile header interaction remains operator acceptance.

## Release / Recovery

Current API: /srv/novelai/releases/20261016T090442 (PID3490097).
Current web: /srv/www/novelai/releases/20261016T090442.
Previous API: /srv/novelai/releases/20261016T064813.
Previous web: /srv/www/novelai/releases/20261016T071424.
Private verified backup: /var/backups/novelai/20261016T090442-account-balance/.
Activation report: /tmp/nai-account-balance-activation-report.json (root0600).

Web fallback retains the compatible current schema4 API for existing tabs.
Before API validation, the helper can restore the known-good previous schema4
API without restoring SQLite/images. No Nginx/unit/credential change was needed.
Broader editor task remains in_progress for operator acceptance.
