# NovelAI Web Workspace

## Goal

Deliver the React/TypeScript/MobX client for the parent workspace; refer to
`../09-22-novelai-image-workspace/prd.md` for authoritative scope and ACs.

## Requirements

- Exchange an admin-issued token for a cookie session; restore it on reload,
  support logout and return to token entry when expired or revoked. No raw
  token or service credential in browser storage or built bundles.
- Compose positive/negative prompts and exactly the supported generation
  settings; show progress, errors and each generated image with download
  metadata while the result is available. List per-user prompt/parameter
  history without saved images; confirm and delete one record at a time.
- Provide one explicit stateless advice input/output, without reading or
  silently editing other workspace state.
- Search Chinese/English tags; show unfiltered NSFW candidates with no switch,
  make the user choose a canonical tag for the positive/negative prompt, and
  visibly attribute/link DanbooruSearch.
- Browser requests use same-origin `/api/*` locally and `/novelai/api/*` in
  production, based on the build-time UI base path. The backend publishes its
  stable OpenAPI contract at unchanged `/api/*` routes.
- Use a NovelAI-inspired dark workspace: a left navigation rail opens basic
  generation settings, while a collapsible bottom drawer contains history,
  tag search and advice. Do not place advice in a right-hand pane.
- Choose canvas width and height together from preset options rather than
  editing either dimension as a free numeric input. Reusing saved history must
  not silently change an older valid dimension pair.

## Acceptance Criteria

- [ ] Session restoration, expiry, revoke and logout UI are implemented; browser
  storage and bundle inspection reveal no raw token/upstream credential.
- [ ] Prompts survive transient failures and the user can inspect/download
  newly generated images while available, revisit parameters after reload and
  selectively delete parameter-history records. Historical images are absent.
- [ ] Advice submission sends only its own input and never mutates the form;
  each submission displays exactly one independent result.
- [ ] Search displays candidate English tags including NSFW where returned;
  only explicit user selection inserts a tag, and cold start/429 errors offer
  retry without losing the draft.
- [ ] Main user journey has keyboard-accessible controls and actionable error
  messages. Frontend automated and browser tests are not part of this task.
- [ ] Dark desktop/mobile layouts keep the left settings control and bottom
  drawer usable without overlapping the prompt, result or each other.
- [ ] Canvas selection offers preset dimensions while preserving non-preset
  dimensions from existing history until the user chooses another preset.

## Dependencies

Consume the backend child's typed OpenAPI/fixture contract; do not parse raw
NovelAI MCP or DanbooruSearch responses in the browser.
