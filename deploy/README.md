# Single-server host deployment

No Docker is used locally or in production. Local development keeps Vite's
HTTPS server and its `/api` proxy; see `apps/web/README.md` and
`apps/api/README.md`. Production uses the existing `www.firesoul.cn` HTTPS
Nginx server, one loopback-only Uvicorn process under systemd, and a private
SQLite file. Keep the existing `/aiqq` route and TLS configuration. Generated
images live only in API process memory and disappear on restart; only tokens,
sessions and generation parameters persist in SQLite.

## Host setup

Install Python 3.12+, `uv`, Node/npm, Nginx and systemd. Keep the API/web
source checkout outside the web root. Create the service account and install
the unit and a private, operator-filled environment file:

```sh
sudo useradd --system --user-group --home-dir /var/lib/novelai --shell /usr/sbin/nologin novelai
sudo install -d -m 0700 -o root -g root /etc/novelai
if ! sudo test -e /etc/novelai/api.env && ! sudo test -L /etc/novelai/api.env; then
  sudo install -m 0600 -o root -g root deploy/.env.api.example /etc/novelai/api.env
fi
if ! systemctl cat novelai-api.service >/dev/null 2>&1 && \
   ! sudo test -e /etc/systemd/system/novelai-api.service && \
   ! sudo test -L /etc/systemd/system/novelai-api.service; then
  sudo install -m 0644 -o root -g root deploy/novelai-api.service /etc/systemd/system/novelai-api.service
  sudo systemctl daemon-reload
fi
```

Skip `useradd` if the account exists, but verify it has the `novelai` group.
The guarded copies are for first installation only. Never overwrite an
operator-owned `/etc/novelai/api.env`; edit it privately when settings change.
Inspect an existing unit with `systemctl cat novelai-api.service` and replace
it only as an intentional upgrade, followed by `systemctl daemon-reload`.
Fill `/etc/novelai/api.env` privately:
`NAI_PUBLIC_ORIGIN=https://www.firesoul.cn` (no path or trailing slash),
`NAI_SQLITE_PATH=/var/lib/novelai/novelai.sqlite3`, and credentials only for
enabled providers. Keep the file root-owned, mode `0600`. The app reads process
environment, not `.env.local`; never copy `.env.local` into a release or web
build. No credential belongs in Vite variables, tracked files, command-line
arguments or the static root. Treat environment and diagnostics as sensitive.
The unit creates `/var/lib/novelai` with `StateDirectory=novelai` and mode
`0700`; only `novelai` writes there. Keep backups and SQLite outside `/srv/www`.

## Stage a release

Use a fresh, immutable release ID and a trusted, clean source checkout. Stage
only the API source and lockfiles so local env files and generated state cannot
enter a release. The staging operator needs write permission for the new
directory; the finished tree is root-owned, readable by `novelai`, and not
writable by the service. These commands assume `sudo`, `uv` and `npm` are on
the operator's `PATH`. Require HTTPS for npm and uv package sources; do not
use an HTTP registry, index, mirror, or an insecure-host override. Before
staging either release, review `apps/api/uv.lock` for HTTPS sources and run
this preflight from the checkout root. It rejects non-HTTPS tarball URLs in
both npm lockfiles and missing integrity hashes. The URL scheme change leaves
the pinned versions and integrity hashes unchanged; `npm ci` still verifies
downloaded archives against those hashes:

```sh
node <<'NODE'
const { execFileSync } = require('node:child_process');
const { readFileSync } = require('node:fs');

const registry = execFileSync('npm', ['config', 'get', 'registry'], { encoding: 'utf8' }).trim();
if (new URL(registry).protocol !== 'https:') throw new Error('npm registry must use HTTPS');

for (const path of ['apps/api/package-lock.json', 'apps/web/package-lock.json']) {
  const lock = JSON.parse(readFileSync(path, 'utf8'));
  for (const [name, entry] of Object.entries(lock.packages)) {
    if (!Object.hasOwn(entry, 'resolved')) continue;
    if (new URL(entry.resolved).protocol !== 'https:') {
      throw new Error(`${path}: ${name} has a non-HTTPS resolved URL`);
    }
    if (typeof entry.integrity !== 'string' || !entry.integrity) {
      throw new Error(`${path}: ${name} has no integrity hash`);
    }
  }
}
NODE
```

Then stage the release:

```sh
release_id=20260924T120000
api_release="/srv/novelai/releases/$release_id/apps/api"
sudo install -d -m 0755 -o "$(id -un)" -g "$(id -gn)" "$api_release"
install -m 0644 apps/api/{pyproject.toml,uv.lock,package.json,package-lock.json} "$api_release/"
cp -a apps/api/src "$api_release/"
(cd "$api_release" && uv sync --frozen --no-dev && npm ci --omit=dev)
"$api_release/.venv/bin/python" -c 'from novelai_api.codex_advice import _cli_path; print(_cli_path())'
sudo chmod -R a+rX "/srv/novelai/releases/$release_id"
sudo chown -R root:root "/srv/novelai/releases/$release_id"
```

Keep `apps/api/node_modules` beside `apps/api/src` in the same release:
`codex_advice._cli_path()` resolves the pinned native Codex binary from that
layout. Do not use a global npm install. The version probe makes no paid
request. Release directories must remain traversable by `novelai`. The
unit's `ExecStartPre` runs `novelai-admin migrate` before one Uvicorn worker
starts; API startup itself never creates the schema.

Build web from the same reviewed source revision. Vite reads `.env*` files in
its working directory and exposes `VITE_*` values to browser code. Stage only
the listed web inputs in a fresh temporary directory: this excludes every
`apps/web/.env*`, including the operator-owned `.env.local`. Run the build
with a clean process environment so no inherited secret can enter the bundle.
Vite needs dev dependencies for the build, so use `npm ci` there (the API
runtime install uses `--omit=dev`). Publish immutable hashed files **before**
switching `current`, so older open tabs can still load their assets:

```sh
web_stage="$(mktemp -d)"
install -m 0644 apps/web/{package.json,package-lock.json,index.html,tsconfig.json,vite.config.ts} "$web_stage/"
cp -a apps/web/src "$web_stage/"
test -z "$(find "$web_stage" -name '.env*' -print -quit)"
(cd "$web_stage" && env -i PATH="$PATH" HOME="$web_stage" npm ci && \
  env -i PATH="$PATH" HOME="$web_stage" NAI_WEB_BASE_PATH=/novelai/ npm run build)
web_release="/srv/www/novelai/releases/$release_id"
sudo install -d -m 0755 -o "$(id -un)" -g "$(id -gn)" "$web_release"
cp -a "$web_stage/dist/." "$web_release/"
sudo chmod -R a+rX "$web_release"
sudo chown -R root:root "$web_release"
sudo install -d -m 0755 -o root -g root /srv/www/novelai/assets
sudo cp -an "$web_release/assets/." /srv/www/novelai/assets/
rm -r -- "$web_stage"
```

Inspect the published files and ensure Nginx can read the release and shared
asset directories. Never publish `apps/web` source, API code, env files,
SQLite, backups or generated images. Keep shared assets for at least the
one-year immutable cache lifetime and any longer open-tab/rollback window;
do not prune them during a release switch. If migrating an existing layout,
copy its still-referenced hashed assets into the shared directory first.

## Start and switch

Add `deploy/nginx-novelai.conf.example` inside the existing HTTPS server block
and check it with `sudo nginx -t` before `sudo systemctl reload nginx`.
`/novelai/` serves the current web release; `/novelai/assets/` serves shared
hashed assets; `/novelai/api/*` proxies to `127.0.0.1:18080/api/*` with the
query string preserved. Exact `/novelai/api` returns 404, and `/novelai`
redirects to `/novelai/`. Do not expose Uvicorn or `/var/lib/novelai` publicly.
`NAI_WEB_BASE_PATH=/novelai/` is required for same-origin API/image URLs.

Nginx preserves the browser `Origin`, replaces client-supplied forwarding IP
headers with `$remote_addr`, and sets the HTTPS forwarding scheme. Uvicorn
trusts forwarded headers only from `127.0.0.1`, because Nginx is its loopback
peer. A hostile process on the same host could also call that port and spoof
those headers; protect host-local access and service accounts. If Nginx is
behind a CDN, configure its trusted `real_ip` sources so login rate limits
see the client address. Proxy buffering, caching and storage are disabled for
transient image responses.

For first start, atomically set the API symlink, start the unit, check local
readiness, then atomically set the web symlink. The release ID must not be
reused; use a new temporary symlink name for each switch:

```sh
sudo ln -s "/srv/novelai/releases/$release_id" "/srv/novelai/.current-$release_id"
sudo mv -Tf "/srv/novelai/.current-$release_id" /srv/novelai/current
sudo systemctl enable --now novelai-api
curl --retry 10 --retry-delay 1 --retry-connrefused --fail http://127.0.0.1:18080/api/health/ready
sudo ln -s "$web_release" "/srv/www/novelai/.current-$release_id"
sudo mv -Tf "/srv/www/novelai/.current-$release_id" /srv/www/novelai/current
curl --fail https://www.firesoul.cn/novelai/api/health/ready
curl --fail https://www.firesoul.cn/novelai/
```

Also check `/aiqq`. These health checks make no paid provider calls. Readiness
verifies the schema and writable SQLite. To issue a token, run `sudo -u novelai
env NAI_SQLITE_PATH=/var/lib/novelai/novelai.sqlite3
/srv/novelai/current/apps/api/.venv/bin/novelai-admin create --label alice`.
The token is shown once; distribute it privately. `novelai-admin list` and
`novelai-admin revoke TOKEN_ID` use the same environment and binary.

For a web-only change with an unchanged API contract, build a fresh web
release from the explicit, env-free inputs above. Publish its hashed assets
first, then atomically switch only `/srv/www/novelai/current` to the new web
release. Verify the public page and its referenced assets, API readiness and
`/aiqq`; retain the previous web release for rollback. Do not restart the API
or migrate SQLite for this case.

For an upgrade, stage both new releases and take a verified pre-upgrade
backup. Review API/web and schema compatibility first. During a maintenance
window, stop the service, atomically switch `/srv/novelai/current`, then
start it and verify readiness **before** switching the web symlink. A brief
API outage is expected; keep traffic closed if the schema change is not
backward compatible. `sudo systemctl stop novelai-api` waits up to 65 seconds
for graceful shutdown; then use `sudo systemctl start novelai-api`. One API
process is required by SQLite and in-memory results. A restart loses transient
images and leaves uncertain paid jobs for the user to review in parameter
history; do not automatically retry them. Inspect failures with
`systemctl status novelai-api` and `journalctl -u novelai-api`.

## Backup and restore

Monitor free space and inodes for `/var/lib/novelai`, the backup target and
logs. Reserve space for SQLite WAL growth and at least one full snapshot.
For an initial policy, keep encrypted off-host daily backups for 7 days and
weekly backups for 4 weeks; adjust to recovery and privacy requirements.
Active parameter history is not age-purged. A backup can retain deleted
prompts and token digests until retention expires, but has no image bytes.

Before a backup intended for an owner-scope restore drill, issue two dedicated
test tokens, retain their one-time plaintext values securely, and ensure each
account already has distinct saved parameter history from approved activity.
The DB stores only token hashes: a token issued after restore is a new owner
and cannot verify access to the earlier owners' history. Do not trigger a paid
generation solely for a deployment drill.

Never copy only a live SQLite file: WAL may hold uncheckpointed writes. The
admin backup command uses SQLite's online backup API, creates an exclusive
mode-`0600` destination, and verifies integrity. Use a new timestamped name
for each run, then move a private copy off-host:

```sh
backup_id=20260924T120000
sudo install -d -m 0700 -o novelai -g novelai /var/lib/novelai/backups
sudo -u novelai env NAI_SQLITE_PATH=/var/lib/novelai/novelai.sqlite3 \
  /srv/novelai/current/apps/api/.venv/bin/novelai-admin backup \
  "/var/lib/novelai/backups/$backup_id.sqlite3"
sudo install -d -m 0700 -o root -g root /private/backups
sudo test ! -e "/private/backups/$backup_id.sqlite3"
sudo install -m 0600 -o root -g root "/var/lib/novelai/backups/$backup_id.sqlite3" \
  "/private/backups/$backup_id.sqlite3"
sudo rm "/var/lib/novelai/backups/$backup_id.sqlite3"
```

Drill restoration on a **new, empty** private directory and an unused
loopback port (18081 below), not on the production file. Choose the API
release compatible with that snapshot; an old snapshot may require the old
API. The drill runs without provider keys and is never added to Nginx:

```sh
drill_id=20260924T130000
drill_dir="/var/lib/novelai-drill-$drill_id"
api_dir=/srv/novelai/current/apps/api
sudo test ! -e "$drill_dir"
sudo install -d -m 0700 -o novelai -g novelai "$drill_dir"
sudo install -m 0600 -o novelai -g novelai "/private/backups/$backup_id.sqlite3" "$drill_dir/novelai.sqlite3"
sudo -u novelai env NAI_SQLITE_PATH="$drill_dir/novelai.sqlite3" \
  "$api_dir/.venv/bin/novelai-admin" migrate
sudo systemd-run --unit="novelai-drill-$drill_id" --property=User=novelai \
  --property=Group=novelai --property="WorkingDirectory=$api_dir" \
  --property=PrivateTmp=yes --property=ProtectSystem=strict \
  --property=ProtectHome=yes --property="ReadWritePaths=$drill_dir" \
  --property=NoNewPrivileges=yes --property=UMask=0077 \
  --setenv="NAI_SQLITE_PATH=$drill_dir/novelai.sqlite3" \
  --setenv=NAI_PUBLIC_ORIGIN=https://www.firesoul.cn \
  "$api_dir/.venv/bin/uvicorn" novelai_api.app:app \
  --host 127.0.0.1 --port 18081 --workers 1
curl --retry 10 --retry-delay 1 --retry-connrefused --fail http://127.0.0.1:18081/api/health/ready
```

Use the pre-backup test tokens to log in through curl's loopback `localhost`
cookie exception for Secure cookies. Run this in a private interactive shell;
the token values go through stdin, not command arguments. Compare both
history responses with the known pre-backup records, then use one Alice job ID
to confirm Bob receives 404. No generation or paid provider call is needed:

```sh
drill_cookies="$(mktemp -d)"
read -rsp 'Alice test token: ' alice_token; printf '\n'
printf '{"token":"%s"}' "$alice_token" | curl --noproxy '*' --fail --silent --show-error \
  -H 'Content-Type: application/json' -H 'Origin: https://www.firesoul.cn' \
  --data-binary @- --cookie-jar "$drill_cookies/alice" http://localhost:18081/api/auth/session
unset alice_token
read -rsp 'Bob test token: ' bob_token; printf '\n'
printf '{"token":"%s"}' "$bob_token" | curl --noproxy '*' --fail --silent --show-error \
  -H 'Content-Type: application/json' -H 'Origin: https://www.firesoul.cn' \
  --data-binary @- --cookie-jar "$drill_cookies/bob" http://localhost:18081/api/auth/session
unset bob_token
curl --noproxy '*' --fail --silent --show-error --cookie "$drill_cookies/alice" \
  http://localhost:18081/api/generations
curl --noproxy '*' --fail --silent --show-error --cookie "$drill_cookies/bob" \
  http://localhost:18081/api/generations
alice_job_id=REPLACE_WITH_AN_ALICE_HISTORY_ID
curl --noproxy '*' --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
  --cookie "$drill_cookies/bob" "http://localhost:18081/api/generations/$alice_job_id"
rm -r -- "$drill_cookies"
```

Do not log token text or send test requests through public Nginx. For a
disposable drill, stop the transient unit, confirm port 18081 is no longer
listening, then remove only that drill directory:

```sh
sudo systemctl stop "novelai-drill-$drill_id.service"
sudo ss -ltn '( sport = :18081 )'
sudo rm -r -- "$drill_dir"
```

Do not reuse a directory containing SQLite WAL/SHM files.

For a real restore, accept the backup's recovery point or stop writes and
take a fresh snapshot first. While the API is stopped, copy the verified
snapshot into a **new** mode-`0700` directory under `/var/lib`, owned by
`novelai`, with only `novelai.sqlite3` mode `0600`. Move the entire old
`/var/lib/novelai` directory aside, then move the fresh directory to
`/var/lib/novelai` on the same filesystem. Never overwrite a live DB or
carry old `-wal`/`-shm` files into the restored directory. Select the
compatible API release before restarting; its migration runs before
readiness. Verify owner-scoped history and sessions before reopening traffic.
Keep the old state directory, API release, web release and pre-upgrade backup
for a bounded rollback window. Rollback by switching the API and web
symlinks to a compatible pair while the service is stopped, then restart and
verify. An API-only rollback is valid only if intervening DB migrations are
backward compatible; otherwise restore its matching pre-upgrade snapshot
into a fresh state directory and accept loss of newer parameter writes. Do
not merge SQLite directories. No generated image can be recovered by design.
