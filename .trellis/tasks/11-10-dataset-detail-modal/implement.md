# Implementation plan

- [x] Inspect thumbnail/detail mounting, state/cache ownership and dialog patterns.
- [x] Implement persistent grid and modal detail, preserving existing actions.
- [x] Reconcile targeted detail mutations and verify selection/session cleanup.
- [x] Run npm lint (ESLint + TypeScript) and an explicit env-free staged build.
- [x] Independent full affected-source check and fixes; no browser/automated tests.
- [x] Update viewer contract and record actual verification/remaining operator UI acceptance.

Agents own only the scoped web source files. Main owns task/spec records.
No production operations or private training data access is authorized/needed.

Final static verification and remaining operator acceptance are recorded in
`verification.md`.

## Authorized frontend-only publication

- [x] Operator explicitly authorized immediate frontend-only publication.
- [ ] Capture current static/API release and API PID; retain old static assets.
- [ ] Commit only reviewed task/source/spec files, excluding unrelated work.
- [ ] Build from exact committed web inputs with locked HTTPS dependencies and
  a clean environment, using `/novelai/` as the production base.
- [ ] Publish new shared assets before atomically switching only the static web
  release pointer. Do not change/restart API, Nginx, private state or active runs.
- [ ] Verify public page/assets, retained assets and health; verify unchanged
  API release/PID and record publication evidence.
