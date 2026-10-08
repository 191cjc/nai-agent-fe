# Host Deployment Contract

## Scope / Trigger

Use this contract when changing `deploy/novelai-api.service`,
`deploy/nginx-novelai.conf.example`, `deploy/.env.api.example`, static release
instructions, or API environment wiring. The operator chose a single-server
deployment without Docker: Vite/FastAPI locally, host Nginx and one systemd
API process in production. Generated image bytes are transient.

## Signatures

- `ExecStartPre=/srv/novelai/current/apps/api/.venv/bin/novelai-admin migrate`
  must succeed before `uvicorn novelai_api.app:app` starts one worker on
  `127.0.0.1:18080`. Uvicorn accepts forwarded headers only from `127.0.0.1`.
- `NAI_SQLITE_PATH=/var/lib/novelai/novelai.sqlite3` is a local file path,
  never a database URL. `novelai-admin backup OUTPUT` creates a new, private,
  verified online snapshot; do not copy a live WAL database file.
- `NAI_PUBLIC_ORIGIN=https://www.firesoul.cn` is the exact HTTPS origin with
  no route path. `NAI_WEB_BASE_PATH=/novelai/` is a Vite build-time path, not
  an API secret or a production systemd setting.

## Contracts

- The systemd unit uses `User=novelai`, `StateDirectory=novelai` with mode
  `0700`, `UMask=0077`, a root-owned mode-`0600` environment file at
  `/etc/novelai/api.env`, and a 65-second stop deadline. The API alone can
  write SQLite. The release under `/srv/novelai/current` is root-owned and
  readable, not writable, by the API user. The unit's private temporary
  directory supports isolated Codex turns.
- Stage only `apps/api` source and lockfiles; install locked Python and npm
  dependencies in that same directory. `codex_advice._cli_path()` resolves
  `apps/api/node_modules` beside `apps/api/src`, so a global CLI install or
  non-editable package layout is not equivalent. Stage web inputs separately
  without `.env*`, run the build with a clean process environment, and publish
  only `dist` under `/srv/www/novelai`.
- Both npm lockfiles and the `uv` lock must resolve package archives through
  HTTPS. The pinned Tencent npm mirror uses HTTPS URLs with unchanged package
  versions and integrity hashes; `npm ci` verifies the downloaded content.
  Before staging, reject non-HTTPS `resolved` values, missing integrity hashes,
  or an HTTP npm/uv registry override. Do not weaken TLS or disable integrity
  verification to make an install pass.
- Host Nginx serves `/novelai/` from a versioned static release through a
  `current` symlink, and immutable `/novelai/assets/` files from a shared,
  retained directory. Publish new hashes before switching the symlink; keep
  old hashes through the browser-cache and rollback window. The more specific
  `/novelai/api/` location rewrites that prefix to backend `/api/`; returned
  transient image links remain backend `/api/*` paths that the web client
  prefixes. Keep `/aiqq` and existing TLS untouched.
- Nginx preserves `Host` and browser `Origin`, replaces client-supplied
  forwarding IP headers with `$remote_addr`, sets HTTPS forwarding headers,
  and disables API buffering, caching and storage. A hostile host-local
  process could still spoof headers by calling the loopback port, so host-local
  workloads are part of the trust boundary. No SQLite, API source, env file,
  backup or generated image belongs under the web root.
- For recovery, restore an online snapshot into a new private directory and
  start a provider-free drill API on unused loopback port `18081`. Two test
  users need securely retained plaintext tokens and distinct history from
  before the backup: the DB stores only token hashes, and newly issued tokens
  cannot own old records. Stop the API before replacing the production state
  directory; never reuse old WAL/SHM files. Roll back API code only against a
  compatible schema, otherwise restore its matching pre-upgrade snapshot.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Missing or malformed `/etc/novelai/api.env` | Service fails before serving; never replace an existing operator-owned env file with the template |
| Missing release binary, unwritable SQLite, or unsupported schema | Pre-start migration or readiness fails; keep public traffic closed |
| Missing NovelAI or Codex credential | Explicit feature returns safe `503`; no paid check is required |
| HTTP package source or missing lockfile integrity | Refuse release staging; use an HTTPS source with verified pinned archives |
| Web base path and Nginx prefix differ | Treat as a release-blocking same-origin route defect |
| Old hashed assets removed during switch | Existing tabs can fail; retain them for the cache/rollback window |
| API restart during generation | No automatic paid retry; transient images disappear |
| Rolled-back API sees a newer incompatible schema | Restore the matching pre-upgrade snapshot, accepting newer write loss |

## Good / Base / Bad Cases

- Good: `https://www.firesoul.cn/novelai/api/auth/session` reaches
  `127.0.0.1:18080/api/auth/session`; only the `novelai` user can read the
  SQLite file, and old tabs still load hashed assets after a release switch.
- Base: without paid credentials, local Vite and FastAPI still serve the UI,
  readiness, login and parameter history; generation/advice report unavailable.
- Bad: bind Uvicorn publicly, bake secrets into Vite assets, put SQLite under
  Nginx's root, overwrite the operator's env file, or copy only a live main
  SQLite file while WAL is active.

## Tests Required

- Static checks may validate the unit, Nginx syntax, shell examples and a
  `/novelai/` web build. Validate both npm lockfiles' URL schemes and integrity
  fields, and the `uv` lock's package URLs, before installing. The operator
  requested no frontend automated or browser tests; no deployment check may
  call a paid provider.
- Before production release, the operator must install the actual release,
  verify systemd startup/readiness and Nginx HTTPS routing, check login and
  owner-scoped history, and rehearse backup/restore in a disposable directory
  on a separate loopback port. Unit verification against absent release paths
  and local Vite startup do not prove production startup.

## Wrong vs Correct

- Wrong: require Compose/Caddy or a Docker image; proxy all `/novelai/` paths
  to the API; install the Codex CLI globally; fetch pinned packages over HTTP;
  copy a live WAL database file.
- Correct: host Nginx serves only built web assets and proxies API paths to
  a loopback systemd service; keep the pinned CLI beside API source; use
  `novelai-admin backup` and a fresh private restore directory.
