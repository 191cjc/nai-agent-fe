# Design

Keep the dataset ReviewGrid mounted for its selection lifetime, still keyed by
set ID + selectionVersion. Render the existing single-image detail in a native
modal/portal above it when an image/task is opened. Reuse existing dialog focus,
Escape and backdrop patterns; close only returns to grid mode, not saved.close.
Preserve existing lazy chunks, selection identity, original-image cache budgets,
request epochs and explicit detail controls. Non-dataset viewing stays inline.

The change belongs to SavedResults.tsx, ReviewGrid.tsx, saved-results.ts and
styles.css as needed. Do not lift the entire review state into a new global
store or duplicate the full detail UI. Add only the targeted bridge needed for
accepted detail metadata (caption/discard/rerun queue) to reconcile into the
retained grid. A normal open/close must leave preview-effect dependencies stable.
Actual filtering membership changes or explicit refresh/purge may invalidate
affected previews as their existing contracts require.

Modal bounds must work on desktop/narrow viewports with bounded scrolling;
native modality makes the retained grid inert. Restore focus to a still-connected
opener with preventScroll or a visible grid fallback if that tile was removed.
Close/replacement/logout abort detail image/metadata work and revoke its owned
full-image URLs; grid URLs remain grid-owned until page/view lifetime cleanup.
Use source review/static checks only under the operator privacy restriction.
