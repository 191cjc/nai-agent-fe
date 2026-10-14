# Web Workspace Contract

## Scope / Trigger

Use this contract when changing `apps/web/src/api.ts`, `store.ts`, `App.tsx`,
or the Vite base path. The frontend handles the user workflow but never owns
provider credentials, durable image storage, or backend authorization.

## Signatures

- `WorkspaceApi(fetcher = fetch, onUnauthorized = () => {})` owns all browser
  requests. Its methods call typed backend `/api/*` routes and `image(path)`
  accepts only returned `/api/generation-results/{id}/images/{index}` paths.
- `AppStore` owns `auth`, `generation`, `history`, `tags`, and `advice` stores.
  `resetProtected()` clears them on logout or session expiry.
- `GenerationStore(api, onSubmitted, onTerminal)` reports accepted submissions
  separately from the first terminal observation of the tracked job.
- `HistoryStore.refresh(): void` refreshes the current page, coalescing behind
  a pending `load(offset)` and following that latest requested offset.
- `NAI_WEB_BASE_PATH` is a build-time, same-origin path ending in `/` (default
  `/`; production `/novelai/`), validated in `apps/web/vite.config.ts`.

## Contracts

- Vite's `import.meta.env.BASE_URL` prefixes browser JSON and validated image
  fetches. Local `/api/*` and production `/novelai/api/*` both reach backend
  `/api/*`; the production proxy strips only `/novelai` on API requests.
  `NAI_PUBLIC_ORIGIN` is the HTTPS scheme and host, with no path.
- The browser stores neither access tokens nor generated images. Token text
  exists only in the login input until exchange; the Secure, HttpOnly cookie is
  browser-managed. Parameter history has no historical image URLs.
- On logout start, hide the workspace and stop generation polling immediately.
  A pending generation POST remains outcome-uncertain until the user checks
  history; a failed logout restores the editable draft, not an automatic paid
  retry. On logout success or `401`, clear protected state and object URLs.
- Advice sends only the explicit advice input and never reads or mutates the
  generation draft. Tag selection inserts only the chosen canonical tag.
- Style, shared text, global negative text and native character descriptions
  remain separate in the draft and saved request. Use the
  [Native Character Prompt Contract](../backend/native-character-contract.md)
  for fields, composition, limits, model validation and provider behavior.
  Character cards have stable draft-only identities; explicit positive tag
  targets must not move to another character when a sibling is removed.
  Removal of the targeted character, reuse and protected-state reset restore
  the shared target. Legacy history restores its flat positive text in shared.
- The prompt editor's compact side tabs replace positive/negative panels in
  the same content area. Hidden negative content reserves no horizontal
  column; tab switching does not reset draft state. Keep visibility local to
  the component and draft content in GenerationStore.
- `Workspace` keeps `settingsOpen`, `drawerOpen` and the active tool tab as
  component-local UI state. `SettingsPanel` edits the existing generation
  draft; the bottom drawer renders history, tags or advice without a right
  tool pane. Closing a panel must not reset its store or trigger a request.
- `TOOL_TABS` in `App.tsx` owns the displayed history/tags/advice order and the
  `Tool` type. Render tabs and compute arrow/Home/End selection from that same
  declaration so the selected panel, roving `tabIndex` and DOM focus agree.
- After its epoch check, `GenerationStore.refresh()` compares the previous
  job ID/status before replacing it. The first succeeded/failed observation
  invokes `onTerminal` before image retrieval, including a resumed job or
  successful result with expired images. Rechecking the same terminal status
  must not invoke it again. `AppStore` routes it to `history.refresh()` without
  awaiting it as part of generation submission or image handling.
- History refresh during a pending page request sets one Boolean intent. Only
  the latest load's epoch-guarded completion may consume it and reload that
  request's offset, including after failure. Consume the intent before the
  follow-up load so a failure alone cannot cause another retry. `reset()`
  clears this intent and invalidates responses. Submission still loads page 0;
  terminal synchronization follows the user's current/requested page.
- Canvas size options in `SettingsPanel` update `draft.width` and
  `draft.height` together through `GenerationStore.setResolution()`. Small,
  standard and large portrait/square/landscape groups are client presets,
  not a confirmed upstream V5 enum or pricing guarantee. A reused history pair
  outside the current UI presets remains selected as a read-only history value
  until the user chooses a preset; do not coerce it on reuse.

## Validation & Error Matrix

| Condition | Frontend behavior |
| --- | --- |
| Invalid returned image path | Reject before `fetch`; never request another origin |
| `401` for active session | Clear protected state and show token entry |
| Failed logout request | Show error, preserve draft, permit retry |
| Generation submission with uncertain result | Block another POST until user acknowledges after checking history |
| History item still queued/running | Disable deletion; backend would return `409` |
| Missing optional tag count/score | Omit the metadata; do not format `undefined` |
| Arrow/Home/End in tool tabs | Select and focus the same tab in displayed order, with arrow wraparound |
| First observed succeeded/failed job | Refresh history independently of image availability/download errors |
| Same terminal result checked again | No duplicate completion-triggered history refresh |
| Completion during history loading/pagination | Coalesce one refresh after the latest request and retain its offset |
| History refresh fails | Set history error; preserve generation result and submission certainty |
| Logout/session expiry with pending refresh | Clear refresh intent and reject stale protected responses |

## Good / Base / Bad Cases

- Good: a production build under `/novelai/` fetches
  `/novelai/api/generations` and a transient image through the same prefix.
- Base: the local `/` build fetches `/api/generations`; history survives a
  reload as parameters only while image object URLs do not.
- Bad: direct browser requests to NovelAI, Codex, or DanbooruSearch; placing
  an access token in Web Storage; retrying an ambiguous paid submission.
- Good: page 20 is loading when generation completes; its latest request
  settles, then one history refresh requests page 20 even if the first load
  failed. Base: an idle history view reloads its displayed page once.
- Bad: terminal completion blindly calls `history.load()` during pagination,
  superseding the requested page with the old displayed offset.

## Tests Required

- The operator requested no frontend automated or browser testing for this
  task. Review the source and API contract manually; do not claim unrun
  runtime, browser, lint, type-check, or build verification.
- Existing lint/type-check and environment-free production builds are valid
  static checks. Review keyboard selection/focus, terminal notification
  deduplication, resumed/expired-image results, pending pagination (success and
  failure), and logout invalidation through the owning source paths. Record
  that source review separately from interactive browser validation.
- When this restriction is lifted, verify both base paths, logout during a
  pending submission, `401` cleanup, and absence of image/token persistence
  with deterministic fake responses only, never paid providers.

## Wrong vs Correct

- Wrong: concatenate a provider URL in a component or fetch an unchecked
  image URL returned by the API.
- Correct: route requests through `WorkspaceApi`; validate backend image paths
  and prefix them with the Vite base path before fetching.
- Wrong: maintain a second keyboard-only tool order or trigger history updates
  from result rendering/image-download success.
- Correct: share `TOOL_TABS` and notify from the epoch-checked job observation;
  use `history.refresh()` for pagination-aware completion synchronization.
