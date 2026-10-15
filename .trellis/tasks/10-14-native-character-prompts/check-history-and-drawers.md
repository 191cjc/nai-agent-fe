# Check: Latest History and Left Tool Drawers

Date: 2026-10-15. Independent `trellis-check` review of the combined current
frontend diff against the latest PRD/design/implementation sections and
`frontend/workspace-contract.md`. Reviewed `store.ts`, `App.tsx`,
`styles.css`, their owning auth/history/generation paths and browser API types.

## Findings (fixed)

None. No source changes were needed.

## Findings (not fixed)

None. No unresolved defect was identified within this change's scope.

## Source Review: History Restoration

- `Workspace` invokes `AppStore.enterWorkspace` on entry. It records the
  authenticated user identity before awaiting history, so React effect replay
  does not duplicate initialization. Cookie restore and login both supply a
  fresh authenticated user; failed logout retains the existing identity and
  does not automatically restore over the current draft after remount.
- Only the accepted initial page-zero response can supply `items[0]`. The
  existing owner-scoped backend contract orders by creation time then ID,
  descending; no status filter or currently viewed page replaces the newest
  item. Empty history performs no reuse; failed history leaves the draft
  usable and reports the existing history error.
- `HistoryStore.load` returns its accepted epoch with its rows. It rejects
  superseded loads both after the network response and before returning.
  `enterWorkspace` rechecks that epoch after its own await. A coalesced refresh
  increments the load epoch in `finally`, invalidating the prior initial
  response before it can restore. Refresh intent still follows the latest
  requested offset and is consumed once, including after failure.
- Every actual draft mutation path increments `draftVersion`: generic fields,
  resolution pairs, character add/edit/remove, tag insertion, reuse and reset.
  Prompt weight controls write through the same field/character setters.
  Reverted edits therefore still invalidate pending restoration. Selecting a
  tag destination alone does not mutate the draft.
- The captured generation revision also includes result/request epoch and
  operation version. Ordinary submissions, experiment start/advancement,
  resume/recheck and result clearing invalidate pending restoration even if
  the operation completes before history settles. Current operation/busy/
  accepted-ID/checking/uncertainty guards additionally prevent reuse while
  generation owns work. Validation-only rejection does not create an operation.
- Logout start, protected reset, session expiry and disposal invalidate entry
  intent. Auth status/user identity is checked again before reuse. Successful
  logout/401 also resets history and generation; stale protected responses
  cannot restore into a later session. Failed logout preserves the draft.
- Automatic and manual restoration share the existing `GenerationStore.reuse`
  mapping: style/shared/negative prompts, native character order with fresh
  client IDs, legacy empty style/characters, every setting, arbitrary historical
  sampler/resolution values and effective seed. The target resets to shared.
- Entry performs one parameter-history GET only. It neither resumes a job nor
  fetches images, submits generation/advice, persists browser data or retries
  paid work. Ordinary history pagination, refresh/deletion and generation
  completion never call automatic reuse.

## Source Review: Left Drawers

- One local active panel controls settings, history, prompt lookup, advice or
  closed. Visible/accessible rail names and order match the request. Native
  disclosure buttons have matching `aria-expanded`/`aria-controls` and stable
  IDs; obsolete bottom tool tabs and their keyboard ordering are removed.
- Settings and all three tools remain mounted with stable keys. `hidden` plus
  the explicit CSS rule removes inactive panels from rendering/focusability.
  Switching preserves manual sampler mode, queries/results/target, advice
  input/output, history page, draft and generation state.
- Active-control toggle, header close, app-scoped Escape and narrow-screen
  backdrop close the panel and return focus to its rail control. Switching
  also redirects focus if it remains inside the panel being hidden. Escape
  respects an already handled event; no new global keyboard listener exists.
- All panels reuse the existing 298px desktop settings column and bounded
  left overlay/backdrop below the 900px breakpoint, including the 48px mobile
  rail offset. The inner panel scroll flexes within the available height.
  Tools use single-column cards, shrinkable inputs and wrapped content/actions.
- Ordinary rail/close/switch handlers do not fetch, submit or reset stores.
  Search/advice/refresh/pagination/deletion remain explicit actions. The
  uncertain-submit action explicitly opens history and loads page zero.
  The separate one-time entry effect remains intact.
- Bottom drawer markup, reserved heights and obsolete selectors/imports are
  removed. The center retains its flexible scroll area. Prompt side tabs,
  ordinary generation results, style experiment viewer and all image URL/
  scheduler ownership remain unchanged.

## Verification

- ESLint: pass, `./node_modules/.bin/eslint .` from `apps/web`.
- TypeCheck: pass, `./node_modules/.bin/tsc --noEmit` from `apps/web`.
- `git diff --check`: pass.
- Frontend/helper automated tests and browser automation: not run, per the
  retained operator restriction. The cases above were source-reviewed, not
  browser-executed acceptance tests.
- No backend checks, provider calls, paid generation/advice, credential access,
  commits or deployment were performed by this reviewer. Fresh build and
  publication verification remain owned by the main session.
