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
- `Workspace` keeps `settingsOpen`, `drawerOpen` and the active tool tab as
  component-local UI state. `SettingsPanel` edits the existing generation
  draft; the bottom drawer renders history, tags or advice without a right
  tool pane. Closing a panel must not reset its store or trigger a request.
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

## Good / Base / Bad Cases

- Good: a production build under `/novelai/` fetches
  `/novelai/api/generations` and a transient image through the same prefix.
- Base: the local `/` build fetches `/api/generations`; history survives a
  reload as parameters only while image object URLs do not.
- Bad: direct browser requests to NovelAI, Codex, or DanbooruSearch; placing
  an access token in Web Storage; retrying an ambiguous paid submission.

## Tests Required

- The operator requested no frontend automated or browser testing for this
  task. Review the source and API contract manually; do not claim unrun
  runtime, browser, lint, type-check, or build verification.
- When this restriction is lifted, verify both base paths, logout during a
  pending submission, `401` cleanup, and absence of image/token persistence
  with deterministic fake responses only, never paid providers.

## Wrong vs Correct

- Wrong: concatenate a provider URL in a component or fetch an unchecked
  image URL returned by the API.
- Correct: route requests through `WorkspaceApi`; validate backend image paths
  and prefix them with the Vite base path before fetching.
