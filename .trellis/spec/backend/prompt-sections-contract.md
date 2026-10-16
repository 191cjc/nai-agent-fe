# Prompt Sections and Private Snapshots

## Scope / Trigger

Use when editing generation composition metadata, prompt section controls,
history/reuse, section tag targets or the private reusable snapshot library.
The original effective prompt fields remain the provider boundary. Editor
metadata belongs only to the authenticated workspace and frozen history/runs.

## Signatures

- `GenerationRequest.prompt_sections: PromptSections | None = None`, excluded
  from both model_dump and model_dump_json when None.
- `PromptSections = {version: 1, shared: SharedSections,
  characters: list[SectionCharacter]}`; at most six complete source characters.
- `PromptSection = {text: str(max_length=3000), enabled: strict bool=True}`.
  Shared keys in order: scene, other. Character keys: character, upper_clothing,
  lower_clothing, action, tags, special, other. All fixed metadata objects reject
  unknown keys; each source character also stores independently validated x/y
  (finite strict floats, default.5, inclusive.1–.9). No draft-only IDs on wire.
- Snapshot create/detail: `{id: UUID, name: str[1,100], entries: list[Entry]}`
  with detail adding created_at. Summary: `{id,name,created_at,entry_count}`.
  Page: `{items: list[Summary], next_offset: int|null}`.
- Shared entry: `{scope:'shared', section:'scene'|'other', text:str}`.
  Character entry adds character_index:int[0,5] and uses the seven character
  section keys. The scope discriminator selects a closed object model.
- GET/POST `/api/prompt-snapshots`; GET/DELETE
  `/api/prompt-snapshots/{id}`. POST201, DELETE204. List limit defaults20,
  inclusive1–100; offset nonnegative and JS-safe; newest then ID order.
- Schema4 adds prompt_snapshots keyed by `(user_id,id)`, entries JSON/name/
  created_at and owner-order index. Explicit migration/readiness and online
  backup remain owned by Database. No generation/image table repurposing.

## Contracts

Composition selects enabled nonblank section texts in fixed order. No texts
returns ''. One returns the exact original text; multiple return trimmed
texts joined by ', '. The effective positive_prompt must equal composed shared
text. Compose every complete metadata person in source order, filter blank
projections, then require exact ordered character_prompts with matching x/y.
Never zip the shorter effective list against unfiltered metadata. Keep legacy
CharacterPrompt nonblank validation and all existing effective limits/model
rules. Hidden/empty metadata cards remain available to history/reuse.

MCP uses its existing explicit effective argument allowlist. Never serialize
metadata, hidden text or snapshot contents downstream. No effective characters
keeps the eleven-field flat payload, regardless of retained hidden cards/mode.
Raw hidden text does not satisfy generation base or all-zero-style preflight.

Old requests/history/runs omit metadata and retain exact old validation and
serialization. Legacy editor restoration puts the whole old shared/character
string into its 其他 section, enabled, without semantic classification. Present
metadata freezes all text/enabled states/source coordinates. style group
generation changes only style/seed, so shared/character metadata stays valid.
Do not broaden canonical same-ID run normalization, rewrite old definition
bytes or discard unknown saved keys; hidden metadata changes still conflict.

Snapshots are immutable, private, durable account data without a seven-day
image expiry. Every new entry/text is bounded, extra fields forbidden, at most
44 entries and at least one nonblank text. Duplicate scope/group/section keys
are invalid. Entries contain only classification/source grouping/text, not
enabled flags, settings, axes, browser IDs or image bytes. character_index is
only grouping inside a snapshot; import exposes actual destination mapping.

POST uses a client UUID: same-owner ID with identical canonical name/ordered
entries returns the original object; changed data conflicts. Composite owner
keys prevent cross-user existence leakage. Each mutation uses existing Origin,
auth and no-store guards; local CRUD never consumes paid queues or providers.
All storage/query paths include user_id. No additional credentials or public
file routes are introduced.

Import offers append/replace and defaults append. Show selected snapshot order;
map shared by key and each source person to a selected existing/new character.
Repeated destinations apply in displayed order; explicit replace's last entry
wins. Preserve duplicate tags and destination enabled state. Validate the whole
proposed draft and apply atomically, retaining original draft on any error.
Per-section import filters exact compatible scope/key and fixes destination.
Saving selected sections creates one named bundle, including hidden text.
Save/import works on incomplete drafts without requiring valid generation
settings or a nonblank base; only relevant section/effective length, position,
cardinality and target checks belong to this local atomic edit. Full request
validation remains at explicit generation submit.

The browser owns one section source of truth and typed helpers for effective
projection. Preserve stable card IDs, exact-section tag targets, keyboard/focus,
0.1 weights/manual editing, draft revisions, reset/reuse/entry guards and deep
frozen requests. Protected snapshot state uses session epochs/abort cleanup and
is cleared on logout/401/disposal. No Web Storage or nested generation forms.
History summaries distinguish source numbering and hidden content from actual
generated prompts. No automatic advice input or paid generation on import.

## Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Metadata absent/null | Preserve old effective format; exclude absent key on serialization |
| Metadata/effective text, order or axes disagree | 422 before seed/history/provider |
| Invalid enabled type, keys, section text or source axes | 422; hidden content remains bounded/validated |
| All people hidden | Empty effective list, flat provider path; full private editor recovery |
| Only hidden base text survives | Existing nonblank base/preflight rejection |
| Snapshot malformed/empty, duplicate key or bad list query | 422 safe ApiError |
| Snapshot same-owner UUID identical payload | Idempotent original object, no duplicate row |
| Same-owner UUID changed payload | 409/prompt_snapshot_conflict |
| Foreign/missing snapshot detail/delete | Generic404; no foreign content |
| Missing session / wrong mutation Origin | 401 /403; no-store |
| Import stale target, >6 people or effective text overflow | Actionable local error; zero partial draft edits |
| Web fallback after schema4 | Retain compatible new API/private DB; no automatic DB restore |

## Good / Base / Bad Cases

- Good: hide lower clothing for a close-up; no hidden text reaches MCP, while
  history restores its exact weights and visibility. A hidden first person at
  (.2,.3) cannot lend coordinates to an enabled second person at (.8,.7).
- Good: save a character's upper/lower sections together, then import that and
  an action snapshot into an explicitly selected person, default append.
- Base: metadata-free native/flat requests and old v1/v2 experiment definitions
  remain byte-compatible; old text enters 其他 during editor restoration.
- Bad: hide only the textarea while still forwarding its text; map imported
  person groups by a filtered provider index; replace existing text implicitly.

## Tests Required

- Offline backend validation/serialization/history/backup/restart tests cover
  strict metadata, mismatched projections, all-hidden/empty source cards, exact
  axes/order and legacy omission. Exact fake MCP assertions prove hidden text
  and metadata are absent in flat/manual/automatic payloads.
- Frozen runs preserve metadata under caller changes/restart, style overrides
  still validate, same-ID changed hidden text/state conflicts and old absent
  metadata definitions remain byte-identical without ordinal replay.
- Snapshot owner/Origin/no-store/bounds/pagination/idempotency/conflict/delete,
  restart/backup and no-provider/no-job side-effect tests use disposable SQLite.
- Schema3->4 preserves existing auth/session/job/run rows and private modes;
  repeated migration/readiness and backups include snapshot records. OpenAPI
  exact additive snapshot has no construction/provider/file side effects.
- Full offline backend frozen sync/pytest/Ruff/lock; web ESLint/TypeScript,
  affected-source review and fresh env-free build. No frontend/helper/browser
  automated tests or paid probes. Real interaction remains operator acceptance.

## Wrong vs Correct

- Wrong: make empty disabled CharacterPrompt valid everywhere or forward a
  request model_dump directly to MCP. Correct: retain strict effective prompts
  and validate a separate optional private editor projection.
- Wrong: revalidate saved definitions to discard unknown keys or serialize
  absent metadata as a new null default. Correct: omit None and preserve raw
  canonical identity, with only the existing missing auto-mode normalization.
- Wrong: silently target source character_index or change destination enabled
  state on snapshot import. Correct: explicit source-group mapping, stable
  destination IDs, text-only atomic application and preserved hidden state.
