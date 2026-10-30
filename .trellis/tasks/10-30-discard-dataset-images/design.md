# Design: Discard dataset images

## Data
Migration `0007_discarded_images.sql` (schema 7):
```
discarded_images(
  user_id TEXT NOT NULL, job_id TEXT NOT NULL, image_index INTEGER NOT NULL
    CHECK(image_index BETWEEN 0 AND 7),
  created_at INTEGER NOT NULL,
  PRIMARY KEY(user_id, job_id, image_index),
  FOREIGN KEY(job_id) REFERENCES generation_jobs(id) ON DELETE CASCADE)
```
Additive; readiness probes the table. Generation delete cascades (foreign
keys are enabled per connection).

## API
- `PUT /api/generations/{job_id}/images/{image_index}/discard` → 204
  (idempotent); `DELETE …/discard` → 204 (idempotent restore). Owner job
  required (`own_job`), `image_index < image_count` of a succeeded job else
  404. Origin middleware applies.
- `GenerationView.discarded_images: list[int]` (sorted). `JobStore` reads
  marks in the same query paths: a single-job read for `view`, and one batched
  query per page for history/experiment pages (no N+1).

## Frontend
- `api.ts`: `discardImage(jobId, index, discarded: boolean)`; type field.
- `SavedResultsStore`: `toggleDiscard()` updates the current job view
  optimistically after the server responds (no optimistic write before 204);
  `hideDiscarded` flag; `move()`/`canNext`/`canPrevious` skip discarded
  images when the flag is on (still lazily loading one image at a time);
  counts for the current experiment from loaded metadata.
- Viewer: badge, 「弃置」/「恢复」 button next to save/seed actions, toggle in
  the toolbar; keyboard arrows follow the same skipping.
- Export (`buildDatasetZip`): skip indexes in `job.discarded_images`, count
  `discarded` separately in progress and the final message.

## Compatibility / rollout
API first (migration at ExecStartPre, backup first), then web. Old web
ignores the new field. Rolling back below schema 7 requires the pre-upgrade
backup (as for schema 6).
