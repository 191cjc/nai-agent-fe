# Prompt Tags and Weights: Independent Verification

- Date: 2026-10-14
- Scope: the complete prompt-tag follow-up, its App integration, and the
  existing draft/request/history/tag-target/auth lifecycle paths.
- Method: source review plus the existing ESLint and TypeScript commands.
  No frontend automated tests, browser automation, provider calls or production
  calls were run by the reviewer. The main session owns the clean build and
  release verification.

## Findings Fixed

1. `PromptEditor.tsx` and `styles.css`: replacing a short textarea with an
   unbounded wrapping tag list during blur could move a lower button between
   pointer-down and pointer-up. Blur now captures the textarea's actual height,
   including a manual resize. The tag region retains that height and scrolls;
   the manual-edit button reserves its footer space even during text editing.
   Hints stay on one line so changing the hint does not increase footer height.
   Browser focus to an external `relatedTarget` is left alone.
2. `prompt-weights.ts`: wrapping an unescaped trailing colon, such as `text:`,
   with a closing `::` produced `:::`, giving an ambiguous closing boundary.
   Such a tag now remains visibly original and manually editable, with weight
   buttons disabled. Internal single colons and escaped trailing colons retain
   the ordinary-tag behavior.

## Source Review

- All four generation prompt categories use the same controlled editor;
  advice retains its independent textarea. Textarea blur writes no draft text.
  Only the explicit manual-edit button sets text mode and requests textarea
  focus. Containers, labels and weight buttons cannot reopen text mode.
  Buttons live outside labels and have explicit `type="button"` and per-field
  accessible names. The hidden manual control is disabled during text mode.
- Tags derive from the current prop on every render. Weight edits first check
  the current source span and then write through the existing field/character
  setters. There is no parsed local copy to become stale after tag insertion,
  history reuse or sibling character removal.
- Source spans preserve untouched commas, newlines, whitespace, repeated tags
  and escape characters. Balanced bracket/numeric scopes prevent splitting at
  their internal delimiters. Unknown/unbalanced scopes remain original text.
  Legacy curly/square emphasis is not assigned a guessed numeric multiplier.
  Complete outer numeric groups retain their inner source while only their
  numeric prefix changes. No A1111 semantic weight is inferred.
- Numeric weights use signed BigInt decimal units, with at least one decimal
  place. The increment is exactly one tenth of the stored decimal scale,
  including extra input precision, zero and negative values. No float rounding
  or undocumented weight bounds are introduced. The 3000-character field
  limit is checked before committing a longer weighted string.
- Existing stable character IDs, add-character focus, removal focus and target
  fallback are preserved. Side-tab order/keyboard handling still shares
  `PROMPT_TABS`; hidden panels use the existing `display: none !important` rule.
- `requestFromDraft` still submits the same controlled strings and ordered
  nonblank native characters. The request/history API representation, reuse
  mapping and result/history summaries require no new field or schema. This
  is source evidence, not a live history round-trip claim.
- `store.ts`, `api.ts`, authentication, uncertain-submit protection, polling,
  history refresh, image handling and advice ownership have no follow-up diff.
  Protected-state reset still clears the draft and its explicit tag target.

## Executed Checks

- `npm run lint` in `apps/web`: **passed**, exit 0. The script runs
  `eslint . && tsc --noEmit`.
- `git diff --check`: **passed**, exit 0 after the source fixes.
- Automated frontend/browser tests: **not run**, per operator instruction.
- Clean production build/public HTTP checks: delegated to the main session;
  not claimed by this review.

## Remaining Acceptance

No unresolved source defect was found within this follow-up's boundary.
Desktop/mobile interaction, keyboard traversal and first-click behavior after
blur still need operator runtime acceptance. Static review cannot establish
real NovelAI numeric-emphasis behavior; the pinned secondary syntax evidence
and unavailable official-document fetch are recorded in
`research/prompt-weight-contract.md`. No real paid output is claimed.
