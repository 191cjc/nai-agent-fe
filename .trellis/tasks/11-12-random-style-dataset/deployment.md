# Deployment

Operator requested "可以部署了" (2026-11-12). Work commit `8c3b25b`.

- API: `/srv/novelai/releases/20261112T084616Z-8c3b25b` (previous `20261112T053918Z-0853c1c` retained)
- Web: `/srv/www/novelai/releases/20261112T084616Z-8c3b25b` (previous retained; shared assets only added)
- Sources exported with `git archive HEAD`; no `.env*` staged. npm locks: 236 HTTPS+integrity entries; uv lock HTTPS only.
- Pre-check (counts only): 0 queued/running jobs, 0 running/stopping runs, schema 13.
- Verified online backup before migration: `/var/lib/novelai/backups/pre-20261112T084616Z-8c3b25b.sqlite3` (novelai, 0600).
- Stop → switch API symlink → start (ExecStartPre migrate). PID 688791 → 742389. Schema 14,
  quick_check ok, `dataset_recipes` empty, failed-job count unchanged (472).
- Web switched after API readiness. index.html and all 9 assets match staged bytes over public HTTPS.
  New recipe routes return 401 unauthenticated; live OpenAPI paths match the committed snapshot.
- No Nginx/env changes, no provider calls, no dataset content read.

Rollback: stop API, repoint both symlinks to `20261112T053918Z-0853c1c`. Schema 14 only adds a
table, so the old API still runs. Recipe draws on newly created runs would be ignored.
Interactive acceptance remains with the operator.
