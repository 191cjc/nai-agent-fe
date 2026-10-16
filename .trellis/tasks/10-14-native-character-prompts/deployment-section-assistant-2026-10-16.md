# Per-section Assistant Deployment

## Result

Published source commit a2fb618 as web-only release20261016T071424 on
2026-10-16 at15:14 China time.

Workspace: https://www.firesoul.cn/novelai/

Every shared/person section plus style and negative headings now has an
助手 button. Its compact anchored popover offers AI advice and tag-search
tabs with independent state. AI consultation is explicitly submitted and
editable, seeded with only current-section label/text; returned prompt text
can be reviewed/edited before explicit append/replace. Search candidates
offer one-click append/replace into the exact stable destination. Hidden state
is preserved, relevant lengths checked atomically, and incomplete generation
settings do not block local valid edits. Left unified tools stay independent.

## Evidence

- Independent full seven-file frontend source review GREEN; no checker source
  correction required. npm run lint (ESLint + TypeScript), whitespace and
  task context validation passed. See check-section-assistant.md.
- Fresh23-input env-free locked build passed for /novelai/. Exact file sets
  and each SHA-256 match the build, working tree and source commit. See
  section-assistant-build-verification.md for artifact hashes.
- Release helper review found a file-set equality gap (listed hashes alone
  could miss a new source file). Parent added exact working/committed/manifest
  set equality and source-symlink rejection; independent re-review passed.
- Root-owned immutable new assets were installed and verified before the
  web current pointer switched. Public HTML/JS/CSS hashes match the build;
  both prior hashed assets and previous release directory are retained.
- Public /novelai/api/health/ready and /aiqq/health return200. API remains
  /srv/novelai/releases/20261016T064813 with PID3446533 before and after the
  switch. No API restart, migration, service/configuration/credential or
  private data/image modification was performed.
- Only frontend source and task/spec artifacts changed. Backend source/tests
  were unchanged; backend tests were not repeated. No frontend/helper/browser
  automated tests, paid advice/generation probes, environment-file reads,
  token creation, push or amend.

## Release and Acceptance

Current web: /srv/www/novelai/releases/20261016T071424.
Previous web: /srv/www/novelai/releases/20261016T064813.
Build source map:
`ec4a08cbc13f1e78b80edc3c2c45da9088b54f74e93ef433b0c4979d124eddd0`.
Local report: /tmp/nai-section-assistant-deployment-report.json.

If the web requires fallback, switch to the retained previous web and keep
the compatible schema4 API/private state. The publication helper restores the
previous web on post-switch verification failure and never touches API state.

Desktop/mobile visual/keyboard interaction and actual AI/search result quality
remain operator acceptance. The broad editor task stays in_progress and other
active tasks remain untouched.
