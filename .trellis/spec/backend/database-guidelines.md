# Database Guidelines

## Scope / Trigger

This API stores access-token digests, revocable sessions and per-user
generation **inputs** in a local SQLite file. When editing `db.py`, migrations,
the admin CLI or backup behavior, keep the database private and never add
generated image bytes to it.

## Signatures

- `Database(path: Path)` resolves the configured `NAI_SQLITE_PATH` as a local
  file path, never as a database URL.
- `Database.migrate()` creates/upgrades the file to `SCHEMA_VERSION` explicitly;
  API startup does not create a schema.
- `Database.connect(write=False)` opens an existing database (`mode=rw`);
  write contexts use `BEGIN IMMEDIATE`, commit on success and roll back on
  failure. Each connection enforces foreign keys and a five-second busy wait.
- `Database.backup(destination: Path)` produces an exclusive, verified online
  SQLite backup; never copy only the active main DB while WAL is in use.

## Contracts

- On POSIX, newly created data directories use mode `0700`, the SQLite DB
  uses mode `0600`, and backup outputs use exclusive mode `0600` creation.
  The migration removes group/other permissions from existing DB/WAL/SHM
  files while preserving owner bits and data. It does not chmod pre-existing
  directories or change the process-wide umask.
- Admin migrations run before API readiness. DB schema lives in
  `migrations/0001_auth.sql` and `0002_generations.sql`, with
  `PRAGMA user_version` and transactional scripts. Store job parameters, effective
  seed, timestamps and outcome; image payloads remain only in process memory.
- Deploy the API on a trusted, private data volume. Existing parent directory
  modes and Windows ACLs require operator review; these POSIX modes do not
  protect against an attacker who can replace paths inside the directory.

## Validation & Error Matrix

| Input / condition | Expected behavior |
| --- | --- |
| New path under an absent directory | Create private parent/data and DB before migrations |
| Existing v1 DB with permissive modes | Restrict DB/WAL/SHM, migrate to v2, preserve records |
| Backup path exists or is a symlink | Reject exclusive creation without overwrite |
| Backup fails after creating destination | Close connections and remove only that destination |
| Missing/unsupported schema | Readiness false / reject future schema version |

## Good / Base / Bad Cases

- Good: after migrating a v1 database, the same issued token and session
  continue working, and owner-only parameter history remains intact.
- Base: running `migrate` twice changes neither version nor auth records;
  a backup contains saved parameters but no PNG bytes.
- Bad: relying on the host's default umask creates a world-readable new DB;
  blindly copying the main WAL database file can lose transactions.

## Tests Required

- Use disposable SQLite paths and no paid/network providers. See
  `apps/api/tests/test_auth.py` for POSIX-permission, upgrade, symlink and
  backup failure tests; see `apps/api/tests/test_generations.py` for online
  backup/restore without images.
- Verify a permissive umask in a subprocess rather than changing pytest's
  global process umask; check WAL/SHM, existing v1 data and mode `0600`
  backups. POSIX-specific assertions should skip on non-POSIX systems.

## Wrong vs Correct

- Wrong: `sqlite3.connect(new_path)` as the first creation step, relying on
  the ambient umask, or `shutil.copyfile(active_db, backup)` under WAL.
- Correct: create the DB with exclusive restrictive mode, tighten existing
  DB/WAL/SHM before migration, and use SQLite's online backup API into an
  exclusively created file.
