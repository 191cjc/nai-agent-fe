# NovelAI Host Deployment

## Goal

Ship a repeatable no-Docker local and initial single-server production
deployment for the parent workspace. The operator superseded the earlier
Compose plan on 2026-09-24. Parent scope:
`../09-22-novelai-image-workspace/prd.md`.

## Requirements

- Keep local Vite HTTPS and its same-origin `/api/*` proxy; run the API as a
  host process. Neither local nor production requires Docker.
- Integrate with the existing `www.firesoul.cn` HTTPS Nginx server without
  replacing `/aiqq`. Serve the UI at `/novelai/` and proxy
  `/novelai/api/*` to the loopback-only `127.0.0.1:18080/api/*`.
- Run one Uvicorn worker as `novelai` under systemd. Migrate before start,
  keep the SQLite path in mode-`0700` `/var/lib/novelai`, and load API secrets
  only from root-owned mode-`0600` `/etc/novelai/api.env`.
- Stage versioned API source under `/srv/novelai/releases` with locked `uv`
  dependencies and the pinned Codex native CLI in sibling `node_modules`.
  Build web with `NAI_WEB_BASE_PATH=/novelai/` and publish shared hashed
  assets before the atomic static `current` switch.
- Require HTTPS package sources and check both npm lockfiles before staging;
  retain pinned versions and integrity hashes when changing mirror URLs.
- Persist parameter history, tokens and sessions, but never generated images.
  Document consistent online backup, disposable restore drills on a second
  loopback port, compatible rollback, and disk/backup retention.

## Acceptance Criteria

- [ ] Local Vite HTTPS and the host API can start with operator-supplied
  configuration, without Docker.
- [ ] Browser and API share one production HTTPS origin; Nginx only exposes
  intended static and proxied routes, not the DB, secrets or loopback port.
- [ ] After restart, owner-scoped parameter history persists; an online
  snapshot restores into a disposable instance without image bytes.
- [ ] Production documentation covers stage/start/switch, health, graceful
  stop, backup, restore drill and schema-compatible rollback.
- [ ] Host deployment and restore are verified by the operator before release;
  this environment does not provide the production host for that drill.

## Dependencies

Production hostname, Nginx TLS, host tooling and secrets are operator inputs.
Do not call paid providers or run browser automation as deployment validation.
