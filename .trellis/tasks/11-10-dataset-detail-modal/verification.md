# Verification

## Result

The dataset grid remains mounted for its existing set ID + selectionVersion
lifetime. Dataset detail reuses the current viewer inside a body-portaled native
dialog; ordinary saved generations and style experiments retain inline detail.
Read-only dialog open/close does not change metadata/thumbnail effect inputs.

Accepted detail caption/discard mutations patch the original retained job/slot,
including after dialog close or navigation. Initial metadata reads replay
accepted field patches. Accepted reruns merge with the queue snapshot by run ID
and freshness; a conservative source replacement floor protects quick picks
until explicit refresh, independently of the actual pending queue count.

## Independent source review

The checker reviewed all four affected source files and relevant protected
session paths. It fixed a replacement-count race between queue snapshot updates
and the React committed reference, plus a final selection/auth guard between a
rerun result and its UI continuation. No remaining findings were reported.

Review covered grid mounting/key/effect stability, page/filter/selection/editor
ownership, thumbnail and full-image URL cleanup, modal focus/fallback, nested
reference-preview Escape events, accepted write/initial-read races, queue
deduplication, and late callbacks after close/replacement/logout/401/disposal.

## Executed checks

- Final `npm run lint` in `apps/web` passed: ESLint and `tsc --noEmit`.
- `git diff --check` passed.
- Fresh isolated staging used the repository lockfile and `npm ci --no-audit
  --no-fund` under a clean environment. It copied only source and explicit build
  inputs, with no `.env*` files.
- The final source build passed with `env -i`, an explicit Node executable PATH,
  `HOME=/home/ubuntu`, and `NAI_WEB_BASE_PATH=/novelai/ npm run build`.
  Vite 6.4.3 emitted the existing-size advisory for the main chunk; no build
  errors. The final build followed the checker's last source fixes.
- All 45 staged source/config/lock inputs matched the final working tree by
  SHA-256. Emitted index script/style references used `/novelai/assets/`.
- Both temporary source/build staging directories were removed after checking.

Final reviewed/built source SHA-256:

| File | SHA-256 |
| --- | --- |
| SavedResults.tsx | dfa01372ff8d3963d07becf1280ea85e2518d986749502fad53dc9c8dc7f2dbe |
| ReviewGrid.tsx | 1214a7bbeb3037602aeeb170fee60e04816c9e28588c377c61bbd209135f9959 |
| saved-results.ts | a6daa09c5423d8fe249ce6b3e08622b1a16c7fdb67fce95aefc3d92ff6cd0cca |
| styles.css | c8011528e93f8b81f876b7dbf247629ac2e7e65a480bbd99f99a978a653e965f |

## Remaining operator acceptance

The implementation gate performed no frontend/helper automated tests, browser
automation, real dataset content inspection, production operations or paid
requests. Static
source review supports the behavior; it is not interactive browser validation.

Operator UI acceptance: open detail on a filtered later grid page, navigate or
edit it, close by X/Escape/backdrop, and confirm retained grid/page/filter/
selection/scroll. Also check narrow-screen scrolling, focus return, and Escape
in a nested reference preview. Subsequent operator-authorized frontend-only
publication is recorded in `deployment.md`; the API was not restarted.
