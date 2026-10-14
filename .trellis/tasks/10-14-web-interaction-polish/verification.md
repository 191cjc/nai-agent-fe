# Web Interaction Verification — 2026-10-14

Branch: `fix/web-interaction-polish`, based on `chore/novelai-api-quality`
at `8720d20`. User approved the final PRD and implementation on 2026-10-14.

## Result

Both scoped fixes are implemented. An independent `trellis-check` agent
reviewed the entire patch and updated frontend contract, found no remaining
defects, and made no additional edits. All six task criteria have evidence
at the agreed static/source-review boundary. Interactive browser acceptance
remains outside this task's validation scope.

| Check | Result | Evidence owner |
| --- | --- | --- |
| `npm run lint` in `apps/web` | Passed, exit 0; ESLint plus `tsc --noEmit` | Implementation agent |
| Full task/spec/source review | Passed; no fixed or unresolved findings | Independent check agent |
| Web lock preflight | Passed; 229 resolved entries use HTTPS and integrity hashes | Coordinator |
| Clean staged `npm ci --offline --no-audit --no-fund` | Passed, exit 0; 179 installed packages | Coordinator |
| Staged `NAI_WEB_BASE_PATH=/novelai/ npm run build` | Passed, exit 0; TypeScript plus Vite 6.4.3 production build | Coordinator |
| Production HTML asset prefix | Passed; references `/novelai/assets/` | Coordinator |
| Staged inputs versus current web source/lock | Exact SHA-256 match after review | Coordinator |
| Trellis implement/check context validation | Passed; four real entries in each manifest | Coordinator |
| `git diff --check` | Passed | Implementation agent and coordinator |
| Frontend automated/browser tests | Not added or run, per the retained operator restriction | All agents |

The reviewer reused the implementation's recorded lint/type-check result
rather than rerunning unchanged checks. No backend, API schema, dependency,
CSS or deployment file changed.

## Behavior Evidence

- **AC1:** `apps/web/src/App.tsx:284` declares `TOOL_TABS` once. Rendering and
  arrow/Home/End calculations use its indices. Source walking confirms both
  arrow wraparounds, history as Home, advice as End, and matching selection,
  panel, roving `tabIndex` and focused DOM index.
- **AC2-AC3:** `apps/web/src/store.ts:230` compares the previous job ID/status
  after the generation epoch check. It notifies only a newly observed terminal
  result, before image handling. A resumed terminal job, absent/expired images
  and failed image downloads therefore still synchronize history; rechecking
  the unchanged terminal job does not notify again.
- **AC4:** `HistoryStore.refresh()` coalesces behind an in-flight load. Only
  the latest request's epoch-guarded `finally` consumes the pending intent,
  retaining that request's captured offset even after failure. Clearing intent
  before the follow-up prevents failure-only retry loops. `reset()` clears
  intent and invalidates stale responses. Source traces cover first-page
  loading, overlapping page requests, success/failure and logout/session expiry.
- **AC5:** `AppStore` owns the completion callback wiring; history requests
  are not awaited as part of generation handling. History errors stay in the
  history store. Generation POST, uncertain-submission protection, typed
  same-origin paths, drafts and temporary-image cleanup retain their existing
  code paths.
- **AC6:** The implementation and independent review reported source walking
  separately from executed static checks. The frontend workspace contract now
  records shared tab order, terminal notifications and pagination-aware
  history synchronization.

## Production Build Isolation

The build used a fresh temporary directory containing only the whitelisted
web manifests/configuration/HTML and `src/`, with no `.env*` source inputs.
The subprocess environment contained only PATH, the normal user HOME, LANG,
explicit npm cache/HTTPS registry/config paths, and the build-time base path.
Distinct empty npm user/global config files excluded private npm settings.
The initial attempt to use `/dev/null` for both config paths was rejected by
npm; using separate empty files resolved this staging-only issue.

The locked offline install required no network request. npm reported its
esbuild postinstall allow-scripts notice; scripts were not approved and the
production build still succeeded. Neither provider credentials nor private
environment files were loaded. No service was started and nothing was deployed.

Staged source/lock/config digest, confirmed against the final reviewed web inputs:

```text
5fe5c26aa7c21ab906f508ac97f356915aea509ae6d7ce574657612f47925980
```

The production output contains `index.html`, `assets/index-CByBY-G2.css` and
`assets/index-sjcNMmKF.js`. Runtime interaction, upstream behavior and
desktop/mobile visual acceptance are not established by this build.

## Remaining Workflow

The user approved the work commit and archive/journal sequence on 2026-10-14.
Commit the approved batch, archive this follow-up and record its journal.
Keep the parent web/API/deployment tasks open for their separate release gates.
