# Production Deployment — Native Character Prompts

## Release

- URL: <https://www.firesoul.cn/novelai/>
- Source: `93e146b38dfd98b6c8b02e4b49f67b1e709db827`
- Branch: `feat/native-character-prompts`
- Release ID: `20261014T085902`
- Web: `/srv/www/novelai/releases/20261014T085902`
- API: `/srv/novelai/releases/20261014T085902`
- Previous web: `/srv/www/novelai/releases/20261014T082041`
- Previous API: `/srv/novelai/releases/20260924T091327`
- Private pre-upgrade snapshot:
  `/var/lib/novelai/backups/20261014T085902-pre-native-prompts.sqlite3`

## Quality and Preparation

Independent full-scope source review found no functional defect requiring
code changes. Frontend ESLint/TypeScript, the clean env-free production build,
211 offline backend tests, Ruff, frozen dependency synchronization, offline
lock consistency and diff checks passed. See the implementation, build and
check verification notes for exact commands and their limits.

The API source and lockfiles were extracted from the committed revision,
excluding env files. Runtime dependencies were installed frozen/offline in
the final versioned path, with the project-local Codex CLI version probe
passing at `0.152.1`. The API source file-map SHA-256 is
`917598d0d6c3a5f329365805df713f7283fa2180834c2ffdda59e6260cd04df5`.
The root-owned API tree is readable/traversable by the service user; a
provider-free schema import as that user confirmed both native fields without
creating a database.

The reviewed web build's source file map matched the committed inputs exactly:
`2066d1687d3316fd2d90762b20e70c401af17ff8907ef65353e2087e9b601642`.
Its root-owned published directories are mode 0755 and files mode 0644. New
hashed assets were fetched successfully before switching the web pointer;
older releases and shared assets were retained.

The private snapshot passed integrity_check and has mode 0600 inside a mode
0700 directory. SQLite remains version 2. Immediately before restart there
were zero queued/running generation jobs, and both the running process and
operator environment file had no configured NovelAI/Codex credentials.

## Switch and Post-Deployment Checks

The API was stopped gracefully, its pointer switched atomically, and systemd
started the new release. Local readiness and the served OpenAPI native fields
passed before switching the web pointer. The usual ExecStartPre migration ran
with no schema version change. API PID changed from `1277439` to `2754998`.
No Nginx configuration/reload, credential update or paid call was performed.

The following public checks all passed with HTTP 200. Page/assets were read
with no-cache and identity encoding headers.

| Path | Verification |
| --- | --- |
| `/novelai/` | Exact new build SHA-256 |
| `/novelai/assets/index-CAQSnE0T.js` | Exact new build SHA-256 |
| `/novelai/assets/index-CjMMQhTO.css` | Exact new build SHA-256 |
| `/novelai/api/health/ready` | Ready |
| `/aiqq/health` | Existing service available |
| `/novelai/assets/index-sjcNMmKF.js` | Previous release asset retained |
| `/novelai/assets/index-CVFHron1.js` | Older asset retained |

Both active pointers resolve to the new release, systemd reports active, and
the new API process still has neither provider credential configured. A
read-only saved-request validation found zero existing generation records;
therefore live history compatibility was not exercised with actual records.
The disposable offline regressions cover both legacy and structured history.

## Rollback and Remaining Acceptance

Prefer a forward fix or retain the new API when falling back to an older
frontend; keep generation unavailable while that UI cannot preserve native
fields. An API downgrade must account for saved request formats, even with
SQLite version unchanged: the old API cannot load new style-only records
whose positive_prompt is empty. Validate saved records against the old model
before downgrading, or deliberately restore a compatible snapshot after
accepting newer-write loss. No rollback or production DB restore was needed.

Desktop/mobile interactive acceptance and real provider output remain pending.
No browser automation or frontend automated tests were run. Image generation
and AI advice remain unavailable until the operator deliberately configures
production credentials. Characters use the verified native default centered
coordinates; six is this workspace's cap, not an upstream hard limit.
