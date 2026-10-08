# Web Design

Follow the parent's `../09-22-novelai-image-workspace/design.md` for route,
auth, error and history contracts. `apps/web` owns a typed same-origin API
client, MobX auth/workspace/history stores, and presentational components for
generation, tag search, advice, transient result gallery and parameter history.
Production builds set `NAI_WEB_BASE_PATH=/novelai/`; the client prefixes both
JSON requests and validated transient image URLs with that path. The proxy
strips `/novelai` and forwards to the backend's unchanged `/api/*` routes.

Only token entry form submission accesses the plaintext token; discard it
after exchange. Session cookies are managed by the browser, not MobX storage.
Keep advice input separate from prompt/parameter state. Poll only the active
authenticated job, cancel polling on logout/unmount, and release image object
URLs. Do not persist generated images in Web Storage; after a reload, history
shows only prompts and parameters. History paging and delete operate on record
IDs returned by the API.

Keep provider-specific fields normalized at the API boundary. Frontend
validation aids UX but backend validation remains authoritative. Loading,
rate-limit, auth expiry and timeout states must not erase draft prompts.
The deployed MCP schema does not enumerate supported `model` or `sampler`
values. Keep these as editable text fields until operator-confirmed values
exist; do not invent a fixed choice list. Display the API's effective seed
and treat image URLs as transient, while saved history stays parameter-only.

The workspace uses a dark, NovelAI-inspired shell: a compact left icon rail
opens the generation settings panel; prompt composition and transient images
occupy the center; a collapsible bottom drawer holds history, tag search and
independent advice. On narrow screens the settings panel overlays the center
and closes with its button, backdrop or Escape. `Workspace` owns only panel
visibility and the selected drawer tab; generation parameters remain in the
existing MobX draft, and all tool stores retain their existing boundaries.

Canvas size is a single preset selector, not independent free width/height
inputs. The client groups portrait/square/landscape choices into small
(`512x768`, `640x640`, `768x512`), standard (`832x1216`, `1024x1024`,
`1216x832`), and large (`1024x1536`, `1472x1472`, `1536x1024`). These are
client presets, not a verified V5 upstream size or billing catalog; do not
claim official compatibility or cost until confirmed without a billable
generation. `GenerationStore.setResolution()` updates both draft dimensions in
one MobX action. When history reuses another valid pair, the selector shows
that history value until the user explicitly chooses a preset. Backend size
validation stays unchanged so older saved parameters remain reproducible.
