# Source findings (no private datasets inspected)

- `apps/web/src/SavedResults.tsx:83` and `:97`: cover and browse both call
  `saved.openExperiment`. Viewer-local `gridFor` starts null around `:250`.
- `apps/web/src/saved-results.ts:149`: opening an experiment calls `loadGroup`;
  `loadGroup` around `:418` unconditionally calls `loadSelectedImage` after metadata.
  Change both mode and image loading to avoid downloading an original before grid.
- `apps/web/src/ReviewGrid.tsx:150`: hide-discarded starts false. Around `:195`,
  tiles use dense original image indexes; around `:236`, quick picks derive from
  discard marks. Both need to omit purged indexes without shifting identities.
- `apps/api/src/novelai_api/generations.py:614`: whole-set deletion removes job
  history and is unsuitable for per-image cleanup. Around `:689`, discard mutation
  is reversible; around `:1130`, page lookups batch markers/captions.
- `apps/api/src/novelai_api/generations.py:934`: ResultStore has only whole-job
  discard. Memory cache currently owns dense GeneratedImage tuples.
- `apps/api/src/novelai_api/image_results.py:239`: version-1 manifest validates
  original member size/hash metadata. Around `:266`, every member must exist for
  any image to be described/read; add deliberate deleted-slot support rather than
  unlinking a member through the existing whole-job operation.
- `apps/api/src/novelai_api/app.py:870` and `:900`: original and thumbnail routes.
  Thumbnail cache hits follow result describe; tombstones must gate cached hits
  and a render finishing concurrently with purge.
- `apps/api/src/novelai_api/db.py:12`: current schema version is 12. New metadata
  needs a migration and updates to schema assertions/upgrade fixtures.
- `apps/api/tests/test_discards.py`, `test_image_retention.py`, and
  `test_api_contract.py`: suitable synthetic owner/isolation/disk/schema patterns.
  Tests must not load real `.env` files or private storage.
- Existing docs prohibit frontend/helper/browser automation. Use source review,
  lint/type-check, and an env-free staged build. No user dataset was read.
