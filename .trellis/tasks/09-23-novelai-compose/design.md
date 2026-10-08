# Host Deployment Design

The 2026-09-24 operator decision replaces the earlier Compose/Caddy design.
Local development runs `uvicorn` on loopback behind Vite's HTTPS dev proxy.
Production adds locations to the existing `www.firesoul.cn` Nginx HTTPS
server, preserving `/aiqq`. Nginx serves only Vite `dist` under
`/srv/www/novelai/current`, serves shared immutable hashed assets from
`/srv/www/novelai/assets`, and replaces `/novelai/api/` with `/api/` when
proxying to `127.0.0.1:18080`. The browser `Origin` is preserved. Nginx
overwrites forwarded client-IP headers; Uvicorn trusts forwarded headers
only from its loopback peer. A hostile host-local process remains in that
trust boundary. Proxy buffering/cache/store stay off for transient images.

`deploy/novelai-api.service` uses `User=novelai`, one Uvicorn worker,
`StateDirectory=novelai` mode `0700` at `/var/lib/novelai`, an explicit
`NAI_SQLITE_PATH` there, and root-owned mode-`0600`
`/etc/novelai/api.env`. Its pre-start migration blocks an unmigrated API.
Versioned source lives under `/srv/novelai/releases/<id>/apps/api`; the
systemd working directory and binaries resolve through `/srv/novelai/current`.
`uv sync --frozen --no-dev` and `npm ci --omit=dev` install locked runtime
dependencies in that same API directory so `codex_advice._cli_path()` finds
the native CLI beside `src`. API releases are root-owned after staging and
not writable by the service.

Before staging, require HTTPS npm/uv package sources and validate both npm
lockfiles' resolved URLs and integrity hashes. The Tencent mirror URLs use
HTTPS with the same paths, package versions, and integrity values; `npm ci`
continues to verify the pinned tarballs. Review `uv.lock` sources for HTTPS.

Build Vite from an explicit copy of web source inputs without any `.env*`
files, using `npm ci` and a clean environment with
`NAI_WEB_BASE_PATH=/novelai/ npm run build`. Publish hashed assets to the
shared directory before atomically changing the web `current` symlink. Keep
old API/web releases and compatible backups for rollback. Upgrade under a
maintenance window: backup, stop API, switch API symlink, start/migrate/check
readiness, then switch static symlink. Any incompatible schema rollback uses
a matching pre-upgrade snapshot, never an old binary against a newer DB.

Only the API can write SQLite. The admin online backup API creates a verified
snapshot, not a copy of the active WAL database file. A drill restores a
snapshot to a new private directory, runs a provider-free API on an unused
loopback port, and checks owner-scoped history using two securely retained
test tokens issued before the backup. Tokens issued after restore cannot own
older history because the database stores only token hashes. Real restore
replaces the entire stopped state directory with a fresh snapshot directory, never mixing
old WAL/SHM. Backups and generated images are never served by Nginx; images
are not stored or recoverable.
