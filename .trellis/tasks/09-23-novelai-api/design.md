# API Design

Use the parent's `../09-22-novelai-image-workspace/design.md` as the contract:
route table, authentication/cookie security, SQLite schema, ephemeral image
results, async generation state machine, provider fault mapping and runtime
isolation. This child implements only `apps/api` (plus contract fixtures).

Group code by auth, generations/storage, tag search, advice, provider clients,
configuration and DB migrations. Keep HTTP/SDK adapters behind injected
interfaces. Use one API process and bounded in-process job workers in the
single-server Compose topology; mark unfinished jobs with unknown outcome at
startup rather than silently resubmitting a paid request. Transient result
routes stream owner-scoped images from bounded memory and expire; never write
generated images to the database, data volume or history.

SQLite backups are operated by the deployment child; provide a safe online
backup path, health/readiness and a migration plan. Prefer additive migrations
so compatible API image rollbacks work. No image-file cleanup or media backup
is needed; an API restart intentionally discards transient image results.
