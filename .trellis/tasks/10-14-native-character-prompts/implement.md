# Implementation Plan

The operator chose native independent characters after the flat-versus-native
compatibility distinction was explained. Implement the recorded behavior.

1. Finish provider research, retaining the credential-free deployed tool schema
   and public source citations. Record default centered positioning and app cap.
2. Backend implement agent owns request validation, native MCP mapping, offline
   regressions and reviewed OpenAPI snapshot. No production/private config edits.
3. Frontend implement agent owns browser types, MobX draft and target behavior,
   prompt UI/styles and structured summaries. Match the public fields in design.
4. Independent check agent reviews the full diff and fixes real defects, checks
   cross-layer round-trip/legacy behavior and runs the required checks.
5. Main session captures contracts and validation evidence, commits the scoped
   change and records session progress. Keep broader parent release gates open.

## Checks

- Backend: frozen offline dependency sync with test/lint extras, offline pytest
  with all provider keys unset, Ruff src/tests, and offline lock consistency.
  Add meaningful cases for model/length/cap validation, schema rejection before
  paid call, exact native mapping, legacy requests, owner-scoped structured
  history and backup/restore. Update OpenAPI for the additive reviewed fields.
- Frontend: npm run lint (ESLint and TypeScript), env-free clean locked build
  with NAI_WEB_BASE_PATH=/novelai/, source review of keyboard focus, stable
  character targets, preservation on panel changes/removal/reuse and reset.
- No frontend automated/browser tests or paid calls. Source review is not
  interactive acceptance or proof of real provider output.
- Run task context validation and git diff --check before the final commit.

## Deployment Considerations

Publishing both layers requires API-first order and a verified private backup
before restarting the API, per deploy/README.md. Check for active jobs first;
an API restart drops transient in-memory images. No schema migration is added
by this feature. Credentials remain unset unless separately configured by the
operator. Keep public page/assets/health and retained rollback targets in the
release record if deployment is performed.
