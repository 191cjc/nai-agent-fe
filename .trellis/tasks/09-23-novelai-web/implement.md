# Web Implementation Plan

- [x] Scaffold typed React/TypeScript/MobX client, route layout and same-origin
  API client against the stable API contract.
- [x] Add session token entry, restoration, logout, auth expiry and protected
  workspace flow with token memory only.
- [x] Add prompt editor, documented parameter subset, submit/poll/errors,
  transient gallery, immediate downloadable images and reproducibility metadata.
  Keep model/sampler editable until the deployed provider accepts verified values.
- [x] Add paginated per-user *parameter-only* history with reuse and confirmed
  single-record deletion; never display historical thumbnails or image links.
  Preserve drafts on failures.
- [x] Add explicit independent advice box and Chinese/English tag search;
  include NSFW candidates, explicit positive/negative insertion and visible
  provider attribution.
- [x] Review the frontend code and API contract without automated or browser
  tests, per the operator's request.

Review gate: no upstream URLs or credentials, raw tokens in browser storage,
implicit advice input, or automatic insertion of top-ranked tags.

## Dark Workspace Revision (2026-09-24)

- [x] Move generation settings behind the left gear control; keep the prompt
  and current result in the center without changing request/state behavior.
- [x] Put history, tag search and advice in a collapsible bottom drawer, with
  left-rail shortcuts and narrow-screen settings overlay.
- [x] Replace the light palette and browser theme color with a dark treatment.
- [x] Pass frontend lint/typecheck and build a clean `/novelai/` release that
  excludes all `.env*` inputs; deploy web-only release `20260924T094207`.
- [ ] Obtain operator visual review on desktop and mobile. No browser or
  frontend automated tests were run.

## Resolution Presets (2026-09-24)

- [x] Replace free width/height inputs with portrait, square and landscape
  options; update the pair atomically without changing API validation.
- [x] Keep a read-only selected history dimension when a reused record does
  not match a current preset.
- [x] Pass frontend lint/typecheck and a clean, env-free `/novelai/` build;
  publish web-only release `20260924T095605` without restarting the API.
- [ ] Confirm the exact upstream/model-specific size catalog before presenting
  any client preset as an official V5 size or cost tier; no paid generation or
  browser test was run.

## V5 Size Tiers (2026-10-08)

- [x] Group portrait, square and landscape client presets into small, standard
  and large in the size selector, keeping standard square as the default.
- [x] Preserve non-preset dimensions reused from history and leave backend
  size validation unchanged.
- [x] Pass frontend lint/typecheck and a clean env-free `/novelai/` build;
  publish web-only release `20261008T025018`. Public UI, asset, API health and
  `/aiqq/health` returned 200 without paid or browser requests.
- [x] Patch the locked build-only `source-map-js` dependency from vulnerable
  `1.2.1` to `1.2.2`, retaining its HTTPS mirror URL and upstream integrity;
  `npm ci`, frontend lint/typecheck and full npm audit pass afterward.
- [ ] Confirm the V5 upstream size/cost catalog and get operator visual review
  on desktop and mobile. Neither paid generation nor browser automation was run.
