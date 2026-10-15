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
- `setPromptTagWeight(source, tag, weight)` updates one validated source span;
  an exact neutral weight removes only its outer numeric wrapper, while
  assigning 1 to a plain tag preserves its source. Unsafe/stale tags return null.
- `HistoryStore.refresh(): void` refreshes the current page, coalescing behind
  a pending `load(offset)` and following that latest requested offset.
- `AppStore.enterWorkspace(): Promise<void>` initializes once per authenticated
  user-object entry. `GenerationStore.entryRestoreRevision` combines draft
  edits and generation ownership epochs. `HistoryStore.load(offset)` returns
  accepted `{epoch, items}` or null; `isCurrentLoad(result)` rejects any load
  superseded after resolution. Entry restoration checks all three boundaries.
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
- In the generation POST catch, the exact typed rejection HTTP 503 with
  `code=provider_unavailable` means no job was accepted under the backend
  contract. Show the not-configured error and leave submitUncertain false.
  Transport errors, unknown 5xx, proxy/non-JSON failures and other status/code
  pairs retain the conservative unknown-outcome lock. Never automatically
  resend either case. Terminal job/provider failures use their existing
  separate meanings and must not be reclassified by this POST-only rule.
  Roll out the backend's dedicated refusal exception before this frontend;
  older APIs caught generic RuntimeErrors under the same pair and cannot
  establish the pre-acceptance boundary. After publishing, retain that backend
  fix even when rolling the web back: open tabs can keep the new classification.
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
- Browser `CharacterPrompt` permits omitted x/y for legacy inputs; every
  `CharacterDraft` owns numeric coordinates defaulting to 0.5. Submit positions
  only for nonblank cards. Reuse preserves coordinates, defaults omitted axes
  and creates fresh stable IDs. Position changes increment `draftVersion` to
  invalidate pending automatic entry restoration.
- `CharacterPositions` shows numbered markers in a responsive board matching
  the generation aspect ratio, with a safe invalid-size fallback. Map x right
  and y down over the full board, clamped to `[0.1, 0.9]` and two decimals.
  Use pointer capture for mouse/touch, clean up up/cancel/lost capture and
  ignore unrelated pointers/buttons. A removed/reused stable ID must never
  transfer its drag to another card. Explicit selection makes overlapping
  markers reachable. Distinguish empty cards, which stay draft-only.
  Focused arrow keys adjust by 0.01; retain focus, Tab order and center reset.
  Dragging never submits. Shared history/result summaries show saved positions.
- The prompt editor's compact side tabs replace positive/negative panels in
  the same content area. Hidden negative content reserves no horizontal
  column; tab switching does not reset draft state. Keep visibility local to
  the component and draft content in GenerationStore.
- `PromptEditor` renders all generation prompt sections (never advice) from
  the controlled draft string. Textarea blur switches to tag view without
  changing that string; only the bottom-right `手动编辑` button reopens and
  focuses the textarea. Tag/container clicks and weight controls never enter
  text mode. Blank new fields may start as text inputs. Capture the textarea's
  actual height on blur and retain footer space; scroll tags inside that
  height so replacing the textarea cannot move a pending pointer-click target.
- Prompt weight buttons change the selected source span by exactly 0.1 using
  decimal arithmetic and NovelAI numeric emphasis (`1.1::tag::`, V4+), never
  A1111 `(tag:1.1)`. Default plain tags display 1.0. Preserve unrelated source
  text and separators; show unknown, incomplete or legacy emphasis as original
  text for manual editing rather than guess a numeric effective weight. Check
  the 3000-character field limit before writing a longer weighted string.
  Treat a plain unescaped trailing colon as original text: adding `::` would
  produce an ambiguous `:::` boundary. Escaped trailing/internal colons remain
  literal text.
- On an explicit assignment or adjustment to exact weight 1, emit the
  selected numeric group's body without its outer `1.0::...::` wrapper.
  Preserve body whitespace, escapes, nested emphasis and surrounding source.
  The shared absolute setter owns this rule for both prompt buttons and style
  experiments. Plain 1.0 needs no wrapper; blur/manual view changes alone
  still leave source unchanged. Other weights retain numeric serialization.
- Derive prompt tags from current props so tag search, history reuse and
  character edits cannot diverge from the submitted prompt. Keep buttons
  outside enclosing labels, use `type="button"`, retain stable character IDs
  and use explicit per-field labels for keyboard/screen-reader access.
- `Workspace` owns one component-local active left panel: settings, history,
  tags, advice or closed. Rail order is Settings, History, Prompt Lookup, AI
  Advice; all panels use the existing settings column on desktop and its
  bounded left overlay/backdrop on narrow screens. No bottom tool drawer or
  reserved bottom tool height remains. The main editor/results keep their
  available vertical space. Explicit settings and uncertain-history actions
  open their corresponding left panel.
- Rail controls use disclosure-button semantics (native Tab/Enter/Space,
  accessible names, aria-expanded/aria-controls), not tabs with a second
  keyboard-only ordering. Clicking an active control, close, Escape or the
  narrow-screen backdrop closes the panel; focus must not remain in hidden
  content. Only the active panel is visible/interactive. Keep settings/tools
  mounted while hidden so manual sampler mode, query/results/target, advice
  input/output and history page survive switching. Closing/switching panels
  never resets stores or submits/fetches; explicit tool actions retain their
  existing behavior. Generation state remains in GenerationStore.
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
- Authenticated workspace entry restores the newest history item's prompts
  and generation settings once, through `GenerationStore.reuse`. Page zero is
  already owner-scoped and ordered by created_at DESC, id DESC; do not filter
  to successful jobs or substitute the last currently displayed page. Reuse
  retains its effective-seed behavior, legacy defaults, native characters and
  arbitrary historical sampler/resolution values. Empty history keeps defaults;
  history-load errors stay visible without disabling the draft.
- Entry restoration must be separate from ordinary history refresh, deletion,
  pagination and generation completion. Use one-time entry state and stale
  response/session guards; a superseded load cannot supply the initial item.
  Any intervening draft edit (including character/position/tag/weight changes), manual
  reuse or generation operation invalidates a pending automatic restore, even
  if the user subsequently returns the draft to the same values. Logout start,
  reset, session expiry and disposal invalidate the response. A failed logout
  preserves the current draft and must not trigger another restore on remount.
  React effect replay must not duplicate initialization. This flow restores
  parameters only, without job resume, image retrieval, provider calls or
  browser persistence.
- Canvas size options in `SettingsPanel` update `draft.width` and
  `draft.height` together through `GenerationStore.setResolution()`. Small,
  standard and large portrait/square/landscape groups are client presets,
  not a confirmed upstream V5 enum or pricing guarantee. A reused history pair
  outside the current UI presets remains selected as a read-only history value
  until the user chooses a preset; do not coerce it on reuse.
- Sampler settings use a visible select with the seven IDs from the pinned
  provider enum recorded in the active task's `research/sampler-options.md`.
  Display a readable name and exact ID for each preset, with an explicit
  manual-entry option. Keep `draft.sampler` the sole submitted string; manual
  mode is local UI state. Selecting manual preserves the current value, typing
  a preset ID manually must not collapse its input, and unknown historical
  values remain editable without coercion. A fresh empty draft still requires
  selection; no automatic sampler default or model-compatibility matrix is
  introduced. Choices do not narrow the free-form browser/API contract.

## Validation & Error Matrix

| Condition | Frontend behavior |
| --- | --- |
| Invalid returned image path | Reject before `fetch`; never request another origin |
| `401` for active session | Clear protected state and show token entry |
| Failed logout request | Show error, preserve draft, permit retry |
| Generation submission with uncertain result | Block another POST until user acknowledges after checking history |
| Generation POST rejects with exact 503/provider_unavailable | Show not-configured error, no unknown-result lock, no automatic retry |
| History item still queued/running | Disable deletion; backend would return `409` |
| Missing optional tag count/score | Omit the metadata; do not format `undefined` |
| Left rail activation / active control again | Open selected left panel / close it; only one visible |
| Close/Escape/mobile backdrop | Hide drawer and avoid focus remaining in hidden content |
| Tool switch/close | Preserve settings/query/advice/history state, with no request |
| First observed succeeded/failed job | Refresh history independently of image availability/download errors |
| Same terminal result checked again | No duplicate completion-triggered history refresh |
| Weight becomes exactly 1 (including decimal equivalents) | Remove only selected outer numeric wrapper; plain source unchanged |
| Sampler preset selected | Write the exact selected ID to the existing draft |
| Manual sampler / unknown reused sampler | Preserve current value in an editable field; do not coerce to a preset |
| Authenticated entry with history | Reuse newest item once, including effective seed and all structured/settings fields |
| Empty/failed entry history | Keep defaults; expose existing history error when applicable |
| Edit/manual reuse/operation before initial history settles | Skip late automatic restore |
| History refresh/page change/failed-logout remount | Never automatically overwrite the draft |
| Logout/reset/disposal/new session before history settles | Invalidate pending restoration |
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
- Good: generation POST rejects with typed `503/provider_unavailable`; show
  the not-configured message without an acknowledgement lock or retry.
  Base: ordinary 4xx keeps its existing specific error. Bad: treating
  `503/request_error`, `502/provider_unavailable` or a network failure as
  proof that no paid job was accepted.
- Good: lowering `1.1::artist:meion::` or raising `0.9::artist:meion::`
  produces `artist:meion`, still displayed at weight 1.0. Base: assigning
  1 to a plain tag leaves it untouched. Bad: blindly removing nested emphasis
  or rewriting unrelated manually entered wrappers on blur.
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
  static checks. Review left-panel disclosure/focus, terminal notification
  deduplication, resumed/expired-image results, pending pagination (success and
  failure), and logout invalidation through the owning source paths. Record
  that source review separately from interactive browser validation.
- Source-review neutral adjustments from both directions and exact decimal
  equivalents, nested/escaped body preservation and plain-tag no-op behavior.
- Source-review sampler names/IDs, blank/preset/manual transitions, history
  reuse and manual typing of a known ID without hiding or resetting the input.
- Source-review initial cookie restore/login, React effect replay, newest-row
  selection, empty/failed history, complete and legacy reuse, edits reverted to
  the original value, character/tag/weight mutations, manual reuse, operations
  that settle before history, superseded/coalesced loads, pagination, failed
  logout/remount, session invalidation and disposal. No paid initialization.
- Source-review side-panel order/toggle/close/Escape/backdrop, desktop/mobile
  bounds and scroll, mounted-hidden content preservation, narrow forms/cards,
  uncertain-history entry and unchanged center/experiment results. Ensure
  hidden tools cannot receive focus and panel switches issue no requests.
- Source-review exact pre-acceptance refusal versus generic/unknown 5xx,
  network failure and mismatched status/code; normal and experiment errors
  stop without a successor POST. Health/readiness alone does not verify image
  provider configuration or successful image generation.
- When this restriction is lifted, verify both base paths, logout during a
  pending submission, `401` cleanup, and absence of image/token persistence
  with deterministic fake responses only, never paid providers.

## Wrong vs Correct

- Wrong: concatenate a provider URL in a component or fetch an unchecked
  image URL returned by the API.
- Correct: route requests through `WorkspaceApi`; validate backend image paths
  and prefix them with the Vite base path before fetching.
- Wrong: leave obsolete bottom tabs or independently open settings/tools;
  trigger history updates from panel switching/result rendering/downloads.
- Correct: one local active left panel with native disclosure buttons; notify
  from epoch-checked job observation and use `history.refresh()` for
  pagination-aware completion synchronization.
- Wrong: classify every 5xx as unknown, or globally translate every
  `provider_unavailable` into an unsubmitted job.
- Correct: recognize only the exact typed generation-POST refusal and retain
  uncertainty for other 5xx; accepted-job errors keep their existing meaning.
