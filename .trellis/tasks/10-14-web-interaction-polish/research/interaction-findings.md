# Workspace Interaction Findings

Recorded 2026-10-14 before implementation. Source anchors refer to the
pre-change revision `8720d20`.

## Keyboard Navigation Owner

`apps/web/src/App.tsx:304` computes an index from an independently maintained
tool order. `apps/web/src/App.tsx:313` then focuses the tab at that index in
the actual rendered DOM, whose order is defined at line 347. For example,
Home currently selects tags while focusing history.

Keep the displayed order as history/tags/advice. Define the tool metadata
once and derive both rendering and keyboard traversal from that declaration.
The selected tool, focus index and roving tabIndex must agree. Avoid expanding
this local fix into a general-purpose tab component or changing the rail's
layout. Source-walk ArrowRight, ArrowLeft, Home, End and wraparound.

## Generation Completion Owner

`GenerationStore.refresh()` owns validated job observations and checks its
epoch before applying them (`apps/web/src/store.ts:214`). A terminal
notification belongs there, before image retrieval, rather than in the
result component or a UI effect. `AppStore` already mediates the independent
generation/history stores (`apps/web/src/store.ts:483`).

Use that existing coordination point for a completion callback. Compare the
previous observation before replacing it so repeated checks of an unchanged
terminal job do not send duplicate notifications. The first observed terminal
state must notify even if tracking resumed directly into a finished result.
Clearing/replacing tracking starts another observation sequence. A queued or
running observation is not a completion event.

Keep the existing submission callback's first-page history refresh separate
from terminal refresh, which preserves the page the user is viewing/requesting.
Do not await history work as part of paid submission or image-result handling.

## History Concurrency

`HistoryStore.load()` currently uses `epoch` to ignore older responses, and
updates the displayed `offset` only after a successful response
(`apps/web/src/store.ts:322`). `reset()` invalidates the epoch and session
version (`apps/web/src/store.ts:357`).

Calling `load()` blindly when completion is observed can supersede a pending
first-page load or pagination request using the old displayed offset. The
background-refresh path should coalesce a terminal refresh behind any current
load, then refresh the page resolved by the latest explicit request. Preserve
existing error reporting and invalidation. Clear any pending background intent
on reset; never loop automatically after a failed refresh.

Review these sequences explicitly:

| Sequence | Required result |
| --- | --- |
| Accepted POST, then running, then succeeded | Submission history update plus one completion synchronization |
| Resumed job is already failed | Failure visible in generation and parameter history |
| Successful job has no image URLs | Completion still synchronizes history |
| Image fetch fails after success | History remains successful; image error is separate |
| Recheck an unchanged succeeded job | No extra completion synchronization |
| Completion while first-page history is pending | Latest history eventually contains terminal status |
| Completion while pagination is pending | User's intended page wins, then refreshes |
| History request fails | History error appears; generation result is preserved |
| Logout before a response settles | No completion notification or history repopulation from stale work |

## Change Boundary and Validation

Product edits belong in `apps/web/src/App.tsx` and `apps/web/src/store.ts`.
The implementation worker owns those files; the coordinator owns task and
spec documentation. No package/dependency, backend or CSS change is expected.
If source inspection exposes a larger issue, report it without widening this
patch. This small task is PRD-only; no separate design/implementation documents
are required.

Use the existing frontend workspace contract and reuse guide. Run the existing
`npm run lint` (ESLint and TypeScript) and a clean production build using
`NAI_WEB_BASE_PATH=/novelai/`. Follow the environment-free web staging pattern in
`deploy/README.md`: explicit source inputs, no `.env*` files, no inherited
provider credentials in the build. A staging script should retain the normal
HOME value and set an explicit npm cache path if needed rather than repurposing
system environment variables. No deployment, paid requests, frontend automated
tests or browser automation are authorized by this follow-up.

Record source review separately from executed lint/build checks; do not claim
interactive keyboard behavior was browser-tested. Restore no deleted frontend
test dependencies.
