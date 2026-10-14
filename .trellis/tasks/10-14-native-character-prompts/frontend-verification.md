# Frontend implementation and source review

## Owned changes

- `apps/web/src/api.ts`: typed style/shared/native character representation and
  a safe `unsupported_character_prompts` message.
- `apps/web/src/store.ts`: structured drafts with stable client-only character
  IDs, a six-card workspace cap, exact style/shared base validation, native
  model validation only for nonblank characters, and prompt-only character
  serialization. Reuse restores ordered sections and defaults legacy history
  to shared text with an empty style and blank editor card.
- `apps/web/src/App.tsx`: stacked style/shared/character editors; add/remove
  controls; vertical positive/negative tabs; model suggestions; explicit tag
  destination selector; and one structured summary for results and history.
- `apps/web/src/styles.css`: compact edge tabs, stacked character cards,
  structured summaries and narrow-screen adjustments.

## Verification performed

- `npm run lint` in `apps/web` passed on 2026-10-14. This runs ESLint followed
  by `tsc --noEmit`.
- `git diff --check -- apps/web/src/api.ts apps/web/src/store.ts
  apps/web/src/App.tsx apps/web/src/styles.css` passed.
- Source review: prompt tabs share one declaration for displayed order,
  Up/Down wraparound, Home/End selection and focused DOM tab. The inactive
  panel has `hidden` plus an explicit `display: none` rule. Its draft text
  remains in the store and the other editor replaces it in the same grid cell.
- Source review: character keys and tag target values use stable draft IDs.
  Removing an earlier character preserves sibling identities and order.
  Removing the targeted character resets the tag target to shared. Removal
  returns focus to Add Character, avoiding a textarea focus event that could
  redirect that fallback or a surviving selected target. Focusing a positive
  textarea intentionally selects it; negative insertion remains explicit.
- Source review: blank cards are filtered before request construction and
  client IDs are excluded. Character prompts never enter the composed base.
  Style-blank requests preserve original shared text; a nonblank style joins
  trimmed nonempty style/shared sections with comma-space for length checks.
- Source review: reuse creates fresh draft IDs, restores section text and
  character order, and resets the selected tag target. Reset replaces all
  structured draft content and tag targeting. Existing session cleanup calls
  reset; submit errors do not replace the editable draft. Authentication,
  polling, completion notification, history refresh and advice are unchanged.

## Pending validation and limits

No frontend automated tests, browser automation, interactive browser checks,
paid image/advice calls or production changes were performed. An environment-
free locked production build and independent cross-layer review are owned by
the main/check session. Desktop/mobile interaction and real provider output
remain pending acceptance; source review does not establish those results.
Native characters use the service's default centered position and the six
verified ordinary V4/V4.5/V5 model IDs; no positioning controls or automatic
placement claim were added. Publishing requires the new API before this UI.
