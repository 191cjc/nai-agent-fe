# User-authorized deployment

The operator requested “部署吧” after reviewing the completed implementation.
The release work commit is `8499310d1361bc8fe60bb6b0243f96cc9115da2a`.
Unrelated `apps/web/README.md` documentation edits were excluded and preserved.

## Published release

- API: `/srv/novelai/releases/20261107T142121Z-8499310`
- Web: `/srv/www/novelai/releases/20261107T142121Z-8499310`
- Public: `https://www.firesoul.cn/novelai/`
- Previous API/web releases and immutable shared assets were retained.
- API source inputs (45) and web inputs (46) match the committed source. Final
  web output: 11 files, 808013 bytes. No env files were staged or published.

## Dependency and maintenance sequence

The initial remote wheel download was slow, so staging reused the tested local
environment and successfully ran `uv sync --frozen --no-dev --offline` against the
same lockfile; test/lint-only packages were removed. Runtime editable source and
entrypoints point to the new immutable release. Locked npm installation and the
pinned advice CLI availability check also passed. No paid probe was run.

Production initially had 16 running jobs in two durable runs. A unique runtime
systemd drop-in temporarily set an unlimited graceful stop deadline, avoiding
the normal 65-second forced-stop risk. Shutdown stopped new claims and waited for
accepted workers to finish. Before migration, zero queued/running generation jobs
remained and the failure count was unchanged at 153. Durable run identities and
cursors were preserved; unfinished work resumed after startup. The runtime
drop-in was removed and the original timeout restored after API verification.

## Private preservation and migration evidence

- Created a private, verified pre-migration schema-12 SQLite online backup under
  `/var/lib/novelai/backups/` after the graceful drain.
- Used only schema/count/status/expiry/size/checksum metadata. No dataset image,
  thumbnail, reference, caption or prompt content was inspected or decoded.
- Schema-13 migration passed integrity and exact existing-table row-count checks
  (11 preserved tables); the new purge table was initially empty.
- Verified all 4849 existing private result/reference files by checksum after
  API startup, before publishing the web. No checksum changes or expired-file
  exclusions were needed at that verification point.
- Private checksum inventories and backup files remain outside source/web trees.
  Deployment did not issue any authenticated image-cleanup request.

## Running checks

- systemd API active; new PID 2882060; service remains loopback-only and runs as
  `novelai`. Operator-owned environment file remains root-owned mode 0600.
- Loopback and public readiness passed.
- Exact running OpenAPI matches the committed schema snapshot.
- New cleanup endpoint rejects unauthenticated sentinel requests with 401 and
  `no-store`, on loopback and public routes; no real dataset IDs were used.
- Public HTML and all 10 new static assets match the staged bytes. Old immutable
  assets remain intact. Existing Nginx syntax verification passed; config was not
  modified.
- Adjacent `/aiqq` and `/aiqq/` returned 502 during the post-deploy check. Its
  systemd service is active; neither its service nor Nginx configuration was
  changed by this deployment. This observation is recorded separately from the
  successful NovelAI release; no unrelated remediation was attempted.

## Acceptance limits

Actual training-set UI interaction is left to the operator. Verification used
source/static checks, synthetic regressions, unauthenticated API/static probes,
and allowed private metadata/checksums. No live/private-image browser probe,
training-content inspection, or real cleanup action was performed by deployment.
