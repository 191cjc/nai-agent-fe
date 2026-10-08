# NovelAI Image Workspace — Delivery Plan

The parent owns the product requirements in `prd.md`, contracts in `design.md`,
the three child tasks and the final integration review. Do not implement on
this parent in parallel with a child; start the child that owns the next
deliverable only after the final planning summary is approved. Do not run
`task.py start` during planning.

## Ordered work

- [x] **Codex security decision:** inspect AiQQ's pinned SDK/CLI and document
  its restricted runtime and post-event tool rejection. On 2026-09-24 the
  operator accepted that isolation instead of a pre-execution all-tools
  denial proof. Do not claim more than the implementation enforces.
- [ ] **MCP compatibility gate:** the deployed `generate_image` tool schema was
  probed with an authorized non-billable request, but model/sampler values and
  actual image payload remain unverified. Record supported values before
  freezing production UI options; never use a billable automated test probe.
- [ ] **Child 1 — `09-23-novelai-api`:** scaffold a fresh FastAPI project
  (do **not** reuse or migrate the discarded PostgreSQL prototype). Add local
  SQLite file storage, admin token CLI, browser sessions and owner checks;
  then implement generation, durable *parameter-only* history/delete, bounded
  transient images, tag search and isolated Codex advice. Freeze OpenAPI and
  fake request/response/error fixtures for the web child.
- [ ] **Child 2 — `09-23-novelai-web`:** implement session restoration/token
  entry, MobX workspace, generation/polling/parameter-history/deletion, explicit advice
  and DanbooruSearch candidate insertion against the frozen API contract;
  verify absence of secrets, raw tokens and stored image bytes in browser
  storage. Returned images can be viewed/downloaded while results are live.
- [ ] **Child 3 — `09-23-novelai-compose`:** after both entry points exist,
  provide host Nginx static assets and same-origin HTTPS API routing,
  systemd-managed FastAPI, a private SQLite file, env/secret templates,
  probes, and consistent SQLite backup and restore instructions. The directory
  name is historical; Docker and K8s/K3s are not release gates.
- [ ] **Parent review:** review fake-upstream API coverage for two users,
  revocation, persistence after restart, deletion, NSFW-visible search,
  advice isolation and startup failure cases; inspect the frontend and its
  build/start without browser automation; perform the host restore drill;
  review PRD AC0–AC8 and record known limitations before release.

Exit each child only when its acceptance checks pass. The backend, web and
deployment children are in progress; runtime release checks remain open. `.env.local` remains
operator-owned and is **not**
automatically regenerated from `.env.example`.

## Verification and risk gates

- Backend (after scaffolding): from a configured `apps/api` virtual environment run
  `python -m pytest -q` and the configured Python lint/typecheck. Tests use
  fake MCP/REST/Codex transports; no billable calls.
- Frontend: code review against the API contract and security requirements.
  The operator requested no automated frontend or browser testing.
- Deployment: start local Vite/FastAPI, check the systemd unit and Nginx
  configuration, deploy the web build to host Nginx, exercise
  health and same-origin routes, restart and verify history persists, then
  rehearse a SQLite database backup/restore on disposable data; ensure no
  generated images or DB connection URL are required as user secrets.
- Auth/security check: cross-user parameter history and transient image result
  access return 404;
  revoked sessions return 401; Cookie flags, Origin checks, logs, API errors,
  API bundles and local DB mounts expose no raw tokens or upstream secrets.
- Provider check: timeout/429/422/cold start, invalid image blocks and partial
  results produce stable errors and leave no persistently stored image bytes;
  a late
  Codex tool-call event fails closed. Never auto-repeat a billable generation.
- Source-control gate: the current workspace is not a Git repository; arrange
  repository initialization or correct working repository before the usual
  Trellis commit/archive flow. Do not run `git init` or commit merely as part
  of planning.

## Release / rollback

Start with safe local fakes, then local Vite/FastAPI, then the single-server HTTPS
deployment after secrets, backup location, domain/certificate and media
memory/DB capacity are configured by the operator. Version web assets and the
API code release separately. For a failed release, stop new generation, restore
the last compatible web assets and API code;
if a migration is incompatible, restore the SQLite database from a consistent
backup before restarting. Automated tests use fakes and never call paid
providers; the deployed app uses configured paid upstreams for authenticated
user actions.
