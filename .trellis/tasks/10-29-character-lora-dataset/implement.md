# Implementation plan

## Backend (apps/api)
1. Migration `0006_reference_images.sql`; `SCHEMA_VERSION = 6`; migration
   test v5→v6 preserving users/jobs/runs.
2. `reference_images.py`: header validation (PNG IHDR / JPEG SOFn), private
   disk store, quota, owner list/get/delete, copy-from-result, in-use guard.
3. `app.py` routes for reference images (raw-body upload, from-result, list,
   bytes, delete); OpenAPI snapshot + expected error map.
4. `generations.py`: `ReferenceUse` optional field on `GenerationRequest`;
   ordinary POST rejects it.
5. `dataset_plan.py`: `styles`, `character` validation (model/mode rules,
   owner references resolved + sha256 frozen), prompt composition and
   rotation in group parameters.
6. `mcp_images.py`: vibe `references`, `image_to_image` call path, schema
   checks, sha256 verification, redacted `record_request`.
7. Tests (fakes only): validation matrix, rotation formulas, vibe/img2img
   arguments at a fake MCP transport, redacted snapshots (no base64 in DB),
   quota/foreign/in-use delete, changed reference bytes → failed group and
   continuation, unchanged legacy dataset/style behaviour, migration.
7b. Trait advice: runner image attachments, endpoint, instructions,
    error mapping; fake-runner tests (attachment paths inside workspace,
    cleanup, owner checks, no persistence). After backend tests pass, ask
    the operator to approve ONE real probe of image input via the relay.
8. Gate: ruff + full pytest.

## Frontend (apps/web)
9. `api.ts` types and reference image methods; `checkedRun` accepts new
   optional fields.
10. `character-prompts.ts` library.
11. Character mode in `DatasetRun.tsx` + reference picker component; store
    action `startCharacterRun`; validation mirroring the server.
11b. Trait-advice button/popover in the character panel.
12. Viewer/history: 「设为参考图」 and per-group reference/style display;
    export include checklist and trait stripping in `dataset-export.ts`.
13. Gate: `npm run lint`, env-free `npm run build`; source review of upload
    errors, quota, stale lists, run lifecycle reuse, Blob URL revocation.

## Specs / docs
14. New `character-dataset-contract.md`; update dataset-run, durable
    experiment, image-retention, database and deployment contracts; README.

## Release
15. Commits: backend, frontend. Deploy API (backup, migration 6, restart
    when idle) then web. No paid probe; operator runs a small real test.
