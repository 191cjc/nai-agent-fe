# Canvas Layout: Independent Quality Gate

## Result and Fixed Findings

GREEN, final source frozen. Independent trellis-check reviewed the complete
affected frontend layer and fixed two local regressions within App.tsx/CSS:

- Saved close shared history-resume's callback and unintentionally closed the
  left tools. Separate closeSavedResult releases saved viewing and focuses the
  current canvas; only history resume additionally dismisses the tool overlay.
- Metadata with auto flex basis could consume all image height when progress
  and prompts were visible, including 600px height above the short breakpoint.
  Figure/metadata now divide remaining height 3:1 with zero bases. Thumbnails
  move to the metadata first row, and a low viewport-adaptive canvas minimum
  plus capped arrow height preserves image space while prompt/progress regions
  can shrink and scroll. Short screens additionally retain minimal prompt and
  nonempty operation scroll regions. No large fixed canvas minimum was introduced.

No outstanding findings. Source inspection covers short/narrow combined states;
it is not runtime visual acceptance.

## Full Affected-Layer Review

- One current-or-saved canvas, contain sizing, local metadata scrolling; current
  job/index selection survives partial arrivals and keeps caption/download/seed
  aligned. Thumbnail/arrow selection reuses loaded URLs without image fetches.
- Prompt disclosure keeps Editor/PromptEditor/experiment config mounted while
  hidden; natural blur-to-tags, tabs, ranges, identities, coordinates and target
  behavior remain intact. Focus cannot remain in hidden drawer/panel content.
- One generation form and persistent form-associated bottom submit button;
  original locks/labels/validation/uncertainty and error/recovery behavior remain.
  Visibility changes cannot create paid work. Explicit ordinary submit reveals
  current results, while reuse/resume use safe after-render navigation/focus.
- Progress/reconnect/Stop and uncertainty actions remain outside the collapsed
  prompt body. Store/API/cache/paid scheduling/auth/entry restoration unchanged.
- Saved arrows/metadata/expiry/cache/session cleanup retain independent URL
  ownership. Explicit close follows existing store cleanup; rendering does not.
- Left tools retain order, mounted state, mobile overlay and safe focus.

## Checks

- Implementer and independent checker: npm run lint (ESLint + tsc --noEmit)
  passed; final git diff --check and context/package discovery passed.
- Read-only build/publication script review and syntax checks passed: fresh
  explicit env-free locked build, committed input/dist/public hashes, web-only
  atomic switch/fallback, readiness/neighboring health/retained assets and
  unchanged API pointer/PID checks. No API restart or config/schema changes.
- No frontend/helper/browser automated tests, browser work or paid calls.
  Unchanged backend was not retested; prior combined release passed356 tests.
- Final source SHA256:

| File | SHA-256 |
| --- | --- |
| App.tsx | 8dca177d49a5c2a024a694a78dae6237533c50f8b629fb2d9ed3b2d4e227fcde |
| SavedResults.tsx | 0572f11a44ac524db68ec820aa1d307dcd7131ba5f805e78b07bd4e1ca0214e7 |
| StyleExperiment.tsx | c40ece976d9fa69bf27b7b98500b6eb139a8313c85a609b7c3026a0e7f18ab66 |
| styles.css | 1beb6cf071ae53bd8b9267e4afdfc356f9d34bc7ed8467ddf2d8c62ffc8b42dd |

Desktop/mobile/real-provider acceptance stays with the operator; broader task
remains in_progress.
