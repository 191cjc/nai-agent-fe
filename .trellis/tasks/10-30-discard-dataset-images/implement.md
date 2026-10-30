# Implementation plan

1. Migration 0007 + `SCHEMA_VERSION = 7` + readiness probe; bump version
   assertions in migration tests.
2. `JobStore`: discard/restore, marks for one job and batched for pages;
   `GenerationView.discarded_images`; routes + OpenAPI snapshot + contract
   test map.
3. Tests (`tests/test_discards.py`): owner isolation, idempotency, invalid
   index/unsucceeded job 404, Origin, cascade on delete, views/pages carry
   marks, migration v6→v7 preserves rows.
4. Web: api, SavedResultsStore toggle/hide/navigation, viewer UI, export
   skip + counts. Gate: lint, env-free build.
5. Specs: image-retention / dataset-run contracts, database guidelines,
   deploy notes. Commit backend and web separately; deploy API then web when
   idle with backup (operator approval).
