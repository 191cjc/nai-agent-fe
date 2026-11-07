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
- Admin migrations run before API readiness. DB schema lives in the ordered SQL
  files under `migrations/`, from `0001_auth.sql` through
  `0013_purged_images.sql`, with `PRAGMA user_version` and transactional scripts.
  Store job parameters, effective
  seed, timestamps and outcome, including optional experiment metadata in
  settings_json. Durable compact run/cursor/seed/Stop state uses the schema3 run table; see
  [Durable Experiments](./durable-experiment-contract.md). Image payloads are stored separately in private seven-day
  disk results; see [Image Retention](./image-retention-contract.md).
- Schema4 adds an owner/id-keyed immutable prompt_snapshots library. Readiness
  probes its table; explicit migrations preserve all existing records. Snapshot
  entries stay in private SQLite and online backups, never image/public files;
  see [Prompt Sections](./prompt-sections-contract.md). Section history metadata
  alone uses existing settings_json and needs no additional generation columns.
- Schema5 adds nullable `generation_jobs.provider_request_json TEXT` without
  rewriting existing rows. Old jobs retain NULL. Readiness probes this column;
  online backups preserve it. Owner-scoped write-once capture uses the existing
  private job lifecycle, not a new public table or image expiry. See
  [Browser API](./api-contract.md) for capture and null-snapshot semantics.
- Schema6 adds owner/id-keyed `reference_images` metadata only. Image bytes
  live in private `reference-images/<user>/<id>` files beside SQLite (not in
  online backups; back them up separately like generation images). Readiness
  probes the table. Provider-request snapshots of reference groups store only
  `{sha256, byte_size}`. See [Character Dataset Runs](./character-dataset-contract.md).
- Schema13 adds owner/job/index-keyed permanent-purge intent and file-cleanup
  completion metadata. Persist intent before physical deletion, preserve pending
  failures for retry, and keep image bytes outside SQLite. See
  [Dataset Review and Cleanup](./dataset-review-contract.md).
- Deploy the API on a trusted, private data volume. Existing parent directory
  modes and Windows ACLs require operator review; these POSIX modes do not
  protect against an attacker who can replace paths inside the directory.

## Validation & Error Matrix

| Input / condition | Expected behavior |
| --- | --- |
| New path under an absent directory | Create private parent/data and DB before migrations |
| Existing v1 DB with permissive modes | Restrict DB/WAL/SHM, migrate through v5, preserve records |
| Existing schema4 job/run/snapshot/session data | Migration5 preserves all values; new request column is NULL |
| Backup path exists or is a symlink | Reject exclusive creation without overwrite |
| Backup fails after creating destination | Close connections and remove only that destination |
| Missing/unsupported schema | Readiness false / reject future schema version |

## Good / Base / Bad Cases

- Good: after migrating a v1 database, the same issued token and session
  continue working, and owner-only parameter history remains intact.
- Base: running `migrate` twice changes neither version nor auth records;
  a backup contains saved parameters and captured provider arguments but no PNG bytes.
- Bad: relying on the host's default umask creates a world-readable new DB;
  blindly copying the main WAL database file can lose transactions.

## Tests Required

- Use disposable SQLite paths and no paid/network providers. See
  `apps/api/tests/test_auth.py` for POSIX-permission, upgrade, symlink and
  backup failure tests; see `apps/api/tests/test_generations.py` for online
  backup/restore without images.
- `test_provider_requests.py` verifies schema4-to5 preservation of sessions,
  jobs, runs and prompt snapshots; repeated migration/readiness; legacy NULL
  values; and captured arguments surviving online backup and restart.
- Verify a permissive umask in a subprocess rather than changing pytest's
  global process umask; check WAL/SHM, existing v1 data and mode `0600`
  backups. POSIX-specific assertions should skip on non-POSIX systems.

## Wrong vs Correct

- Wrong: `sqlite3.connect(new_path)` as the first creation step, relying on
  the ambient umask, or `shutil.copyfile(active_db, backup)` under WAL.
- Correct: create the DB with exclusive restrictive mode, tighten existing
  DB/WAL/SHM before migration, and use SQLite's online backup API into an
  exclusively created file.
