# Host Deployment Plan

- [x] Remove Compose, Caddy, Dockerfiles and Docker-only ignore files while
  retaining the existing Vite HTTPS local flow.
- [x] Add one-worker systemd API unit with pre-start migration, loopback
  binding, loopback-only forwarded-header trust and private state/env paths.
- [x] Update Nginx example and document locked release staging, static asset
  switch, token CLI, health, backup, disposable restore and compatible rollback.
- [x] Switch the API and web npm lockfile mirror tarballs to HTTPS only,
  preserving metadata and integrity hashes; gate host staging on HTTPS sources
  and a lockfile preflight.
- [x] Stage disposable host-style releases: offline `uv sync --frozen --no-dev`
  and `npm ci` resolve the pinned API CLI; a provider-free API starts and
  reports ready; the `/novelai/` web build completes from the HTTPS lockfile.
- [x] Statically validate the unit, Nginx paths, JSON task files and absence
  of stale container instructions in owned deployment files. Do not run paid
  providers, frontend/browser automation or a host restore in this workspace.

Release gate: the operator must test the installed Nginx configuration,
systemd startup/readiness, and a disposable SQLite restore on the target host.
The production one-origin and no-persisted-image boundaries must hold.

## Host Rollout (2026-09-24)

- [x] Install release `20260924T091327` with locked API dependencies and a
  `/novelai/` production web build; keep provider credentials unset.
- [x] Start the one-worker API under systemd and verify loopback readiness.
- [x] Add only `snippets/novelai.conf` to the existing HTTPS server, validate
  Nginx, and verify the public page, asset and readiness routes plus `/aiqq`.
- [x] Verify a private online SQLite backup and a disposable restored API on
  loopback port 18081; stop and remove the drill instance.
- [ ] Configure encrypted off-host backups and repeat the restore drill with
  two approved accounts and pre-existing parameter history.
- [ ] Privately configure provider credentials and verify actual NovelAI/Codex
  behavior only with explicit operator approval for billable calls.
- [x] Switch web assets only to dark-workspace release `20260924T094207`;
  leave the API release and existing `/aiqq` route unchanged.
- [x] Switch web assets only to resolution-preset release `20260924T095605`;
  verify the public assets, API readiness and `/aiqq` without paid calls.
- [x] Switch web assets only to small/standard/large size-tier release
  `20261008T025018`; verify public UI and asset, API health and `/aiqq/health`
  without changing the API release or calling paid providers.
