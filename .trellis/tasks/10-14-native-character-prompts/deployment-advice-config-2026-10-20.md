# Advice Configuration Enablement Deployment

Published source commit d55b939 as API-only release 20261020T095317 at
2026-10-20T09:54:02.730030+00:00 (17:54 China time).

Workspace: https://www.firesoul.cn/novelai/

## Diagnosis and authorized result

The reported advice/translation failure was503 advice_unavailable. The running
API and private operator configuration had no NAI_CODEX_API_KEY. General
readiness was healthy because it checks SQLite, not advice availability.

The user explicitly authorized reusing existing AiQQ AI configuration and
requested the future key location. Added optional validated backend endpoint
and model settings, then privately copied only AiQQ's selected text-AI key,
HTTPS endpoint and model into /etc/novelai/api.env. It is a one-time copy;
AiQQ's configuration and service are unchanged. No secret values were emitted,
committed, placed in argv or exposed to web assets. Future changes are independent.

## Validation and actual release evidence

- Independent full affected-backend check GREEN with no product corrections:
  748 offline fake tests, frozen sync/offline lock, Ruff src/tests and exact
  unchanged OpenAPI. Backend has no configured type checker. Frontend unchanged;
  no frontend/helper/browser tests or frontend build required.
- Exact committed/working/staged API source sets and hashes match. Frozen
  offline runtime dependencies and adjacent CLI0.152.1 installed; side-effect-free
  exact OpenAPI and disposable schema4/SQLite/readiness probes passed.
  API source-map SHA-256:
  a4a9e251cebc575dd6f000cb1a1745d775afcd332441429b676139037989197c.
- Verified private online SQLite backup plus root0600 original environment backup
  preceded the configuration change/restart. Zero active jobs/runs before restart
  and after graceful shutdown; existing auth/session/job/run/snapshot records,
  schema4 and unrelated NovelAI/provider settings preserved. No database restore.
- Configuration was validated through Settings and app runner construction with
  private stdin and no lifespan/DB creation/model request, both before restart
  and using the new process's exact selected settings. The running process has
  the copied key/base/model, with all unrelated configuration unchanged.
- New API PID669990; exact running OpenAPI and public/loopback readiness pass.
  Public unauthenticated balance remains401/no-store without a provider call.
- All74 retained result sets and74 PNGs preserve exact manifest/image bytes and
  original expiry; none expired during release. Private owner/modes verified.
- Web release/pointer remains20261020T091846; exact public HTML/JS/CSS hashes
  and retained assets match baseline. AiQQ PID291610, source configuration bytes
  and /aiqq/health remain unchanged/healthy.
- Real AI/provider/advice/image calls:0. No token issuance or changes to AiQQ,
  Nginx/unit/frontend. These checks verify configured wiring and preservation;
  remote credential/model compatibility, actual translation quality and latency
  remain operator acceptance. Broader editor task stays in_progress.

## Locations and recovery

Current API: /srv/novelai/releases/20261020T095317.
Previous retained API: /srv/novelai/releases/20261020T091846 (prior PID657285).
Unchanged web: /srv/www/novelai/releases/20261020T091846.
Private backup: /var/backups/novelai/20261020T095317-advice-config/.
Root0600 activation report: /tmp/nai-advice-config-activation-report.json.

Use sudoedit /etc/novelai/api.env to change NAI_CODEX_API_KEY. Optional endpoint
and model are NAI_CODEX_BASE_URL and NAI_CODEX_MODEL in the same file. After
editing, restart novelai-api.service only when generation/experiments are idle;
no frontend rebuild is needed. Keep the operator file/backups private.

Retain the modern API process/pointer/configuration after its startup attempt
if later validation fails; diagnose and forward-fix rather than automatically
stopping/restarting accepted work or restoring live data. Baseline API/original
config recovery is restricted to failures before modern startup.
