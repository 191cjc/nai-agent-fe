# Single-server SQLite parameter-history design

Checked 2026-09-23 against primary documentation:

- SQLite's online backup API safely snapshots a database during writes:
  https://www.sqlite.org/backup.html
- SQLite WAL allows readers alongside one writer; account for a live WAL file
  instead of blindly copying only the main database file:
  https://www.sqlite.org/wal.html
- Docker named volumes outlive containers:
  https://docs.docker.com/engine/storage/volumes/

Revised product decision: use the AiQQ-style local SQLite file for user/token/
session metadata and saved generation *inputs* (positive/negative prompts,
settings, effective seed, timestamps and status). The API alone mounts its
private durable data volume. Do not persist generated image bytes in SQLite,
the volume or backups. Keep returned images in bounded in-process memory only
long enough for the current authenticated user to view/download them, then
discard by TTL and on shutdown. Image download history is intentionally absent.

SQLite is an appropriate fit for this approved one-API-process, single-server
Compose deployment, but it permits only one concurrent writer. Use bounded
generation jobs and avoid multiple competing DB-writing processes. On backup,
use SQLite's online backup API or an equivalent verified consistent snapshot;
restore drills check token/session and parameter history, not images. A
deleted history record can remain in backups until their separately documented
retention expires. Monitor DB-volume capacity so missing space doesn't silently
discard user inputs.

Implementation reset 2026-09-23: the incomplete PostgreSQL scaffold was
removed, so build the first migration directly for SQLite; do not plan a
PostgreSQL-to-SQLite data migration. Store the database at a configurable
private file path, not a database URL. The previous `.env.local` is
operator-owned and may still have obsolete database/media fields; do not
silently rewrite or print its values during planning.
