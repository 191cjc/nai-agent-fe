# Host Deployment Contract

## Scope / Trigger

Use this contract when changing `deploy/novelai-api.service`,
`deploy/nginx-novelai.conf.example`, `deploy/.env.api.example`, static release
instructions, or API environment wiring. The operator chose a single-server
deployment without Docker: Vite/FastAPI locally, host Nginx and one systemd
API process in production. Generated images use private seven-day disk retention;
see [Image Retention](./image-retention-contract.md) and
[Durable Experiments](./durable-experiment-contract.md) (introduced schema3)
and [Prompt Sections](./prompt-sections-contract.md) (current schema4).

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

- Experiment zero omission originally shipped at schema3 and introduced definition plan_version2.
  Publish its compatible API before the web and retain that API on web fallback.
  Once any v2 run definition has been accepted, the old schema3 API is also an
  unsafe fallback: it interprets zero as emphasis and ignores the new version.
  Before API validation, an emergency old-API fallback requires a read-only
  check proving no stored v2 definitions. Never restore the live database.
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
  only `dist` under `/srv/www/novelai`. Compare the exact web input file set
  (src files plus explicit root build inputs) across clean-build manifest,
  working tree and committed git tree before per-file SHA-256 checks. Checking
  only listed manifest hashes misses a newly added source file after a build.
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
  authenticated image links remain backend `/api/*` paths that the web client
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
  compatible schema and saved parameter format, otherwise restore its matching
  pre-upgrade snapshot after accepting newer-write loss. Native style-only
  records can fail an older API's positive-prompt validator despite the same
  SQLite version; see [Native Character Prompt Contract](./native-character-contract.md).
- Coordinate upgrades are API-first too: the earlier native API ignores x/y
  and hardcodes center. Verify the running additive OpenAPI before web
  activation, keep the new API during web fallback for already-open tabs,
  and preserve provider configuration. Back up privately and inspect active
  jobs before restarting; this additive change needs no DB restore/migration.
- Automatic-position upgrades also require API-first publication: an older API
  ignores auto_character_position and sends saved x/y as manual placement.
  Verify the additive strict-boolean/default-false OpenAPI before switching
  the web. Keep the new API on web fallback for already-open tabs and accepted
  automatic-mode history/run snapshots; never restore the live database.
- Prompt-section snapshot rollout requires explicit migration4 after a private
  verified online schema3 backup and idle/shutdown checks. Verify preserved
  existing rows/config/images and new-table readiness before API-first web
  publication. Schema3 API code rejects schema4 even with an empty library;
  retain the compatible API once migration4 commits, including web fallback.
  Never automatically restore the live DB or start schema3 code after commit.
  Check unauthenticated new snapshot routes return401 with no-store on both
  loopback and public paths. For image preservation evidence, capture private
  manifest/PNG SHA-256 inventory while the API is stopped, then verify exact
  bytes and original expiry for every still-unexpired result after startup.
  Root-directory existence/permissions alone do not verify retained images.
- Individual tag comments require an API-first release at unchanged schema4.
  Old APIs ignore prompt_comments and may submit hidden style/negative source.
  Verify the strict optional boolean in exact running OpenAPI before web
  activation. Once the modern API has started, keep it during web fallback or
  use a forward fix: even pre-validation startup may have accepted flagged
  history/runs. SQLite schema compatibility alone cannot authorize a downgrade.
  Preserve idle/backup/config/image/expiry gates and never restore the live DB.
- Account-balance rollout adds a read-only authenticated route at existing
  schema4. Publish the API before web, preserving private state/config/images
  and idle/backup gates; no migration is needed. A configured adapter probe
  verifies only read-only get_subscription normalization, not authenticated
  browser-route success. Keep real-route401/no-store checks separate from
  fake authenticated-route tests; never create a token or paid probe just to
  verify a header balance. Cached fetched_at remains the original fetch time.
- Advice-instruction updates can require API-first publication despite an
  unchanged OpenAPI/schema: publish explanation-aware instructions before the
  section translation UI. Preserve idle/backup/configuration/image gates.
  Once modern API startup has been attempted, a failed readiness/schema/config
  or image verification must leave that process and release pointer intact
  for diagnosis and a forward fix. It may already have accepted new work;
  a recovery branch must not stop/restart it merely to retain the same code.
  Baseline API recovery is limited to failures before modern startup.
- API/database readiness does not prove AI advice is configured. Before
  reporting advice/translation enabled, verify the running API has its selected
  `NAI_CODEX_API_KEY` and optional endpoint/model, and validate runner wiring
  without starting a turn. Treat real upstream success as separate acceptance.
  With explicit authorization, copy only the selected key/base/model from an
  existing service into root0600 `/etc/novelai/api.env`; back up the original
  config privately, preserve unrelated settings, and leave the source service
  untouched. This is a one-time copy, not automatic cross-service syncing.
  Never print secrets or pass them in command arguments. Future rotations use
  `sudoedit /etc/novelai/api.env` and an idle API restart. Recover original
  configuration automatically only before modern startup is attempted.

- Retained images live under /var/lib/novelai/generation-images/, service-owned
  with 0700 directories/0600 files, outside the immutable release/web trees.
  Keep this private directory during code switches; no new Nginx alias or unit
  writable path is needed. API-first retention rollout verifies its private
  root and OpenAPI before web. Keep the retention API during web fallback.
  SQLite online backup excludes images; separate private image backup is
  required for host recovery. Preserve original expiry when restoring files.

- Durable experiments require migration3. Verify a private online v2 backup,
  zero active jobs/runs, stop API, run the staged service-user migration and
  verify schema3/integrity/auth+job counts before API readiness and web switch.
  After schema3 commit retain the new API even if the web falls back. Do not
  restore the live DB or start the older schema2 API as rollout recovery.
  In a disposable recovery drill, disable/stop copied runs before application
  lifespan; a restored scheduler must never reach real configured providers.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Missing or malformed `/etc/novelai/api.env` | Service fails before serving; never replace an existing operator-owned env file with the template |
| Missing release binary, unwritable SQLite, or unsupported schema | Pre-start migration or readiness fails; keep public traffic closed |
| Missing NovelAI or Codex credential | Explicit feature returns safe `503`; no paid check is required |
| HTTP package source or missing lockfile integrity | Refuse release staging; use an HTTPS source with verified pinned archives |
| Web base path and Nginx prefix differ | Treat as a release-blocking same-origin route defect |
| Old hashed assets removed during switch | Existing tabs can fail; retain them for the cache/rollback window |
| API restart during generation | No automatic paid retry; unexpired completed disk images survive |
| Web fallback after durable schema3 migration | Retain compatible new API/private state; never start schema2-only API or restore live DB |

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
