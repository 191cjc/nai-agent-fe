# Research: Prompt sections and private snapshots

- Query: Preserve shared/character section text and hidden state across generation history and frozen experiments without forwarding hidden text; identify the smallest durable private snapshot store and section-targeting consumers.
- Scope: internal
- Date: 2026-10-16

## Findings

### Confirmed product inputs and recommended contract

The parent supplied these confirmed requirements: shared input has `场景` and `其他`; each character has `角色`, `上半身服饰`, `下半身服饰`, `动作`, `标签`, `特殊`, `其他`. Each section retains PromptEditor/weight behavior and has Hide, Save and Import actions. Checkboxes select multiple sections for one named snapshot. Global import selects multiple snapshots and can map them to target characters. Import offers append/replace, defaults to append, and does not automatically change the destination section's hidden state. Snapshots save section text and classification only; generation/history metadata additionally saves enabled state and coordinates. These are product inputs, not discoveries from the existing implementation.

**Final authority: `../prompt-sections-design.md`.** Exact character keys are `character`, `upper_clothing`, `lower_clothing`, `action`, `tags`, `special`, `other`. Legacy text goes verbatim into `其他`. One composed part preserves raw text; multiple parts trim/join with `, `. Earlier `role`/`upper_body` names and legacy 场景/角色 placement were unadopted candidates. Snapshot composite owner/id key is confirmed. The final design agrees with the source boundaries below and supersedes optional research alternatives.

Recommend the parent's minimal additive design:

- Keep `positive_prompt` and `character_prompts` as the actual enabled-text projection. Keep the existing nonblank CharacterPrompt validator and the provider adapter's existing native gates.
- Add optional `GenerationRequest.prompt_sections`, default `None`, omitted from both JSON and Python dictionary serialization when None. Existing `experiment` already demonstrates `Field(default=None, exclude_if=lambda value: value is None)` at `apps/api/src/novelai_api/generations.py:101`.
- A complete present metadata object contains a fixed shared section map, plus the complete ordered character workspace list. Each section has original `text` and strict boolean `enabled`; each character metadata object has all seven sections and validated x/y. Do not persist draft-only character IDs.
- Use the final design's version1 fixed typed metadata fields and forbid unknown keys; do not accept arbitrary section names.
- One deterministic composer walks the fixed section order and selects enabled nonblank text: none yields empty, one preserves its exact original string, multiple trim for joining with `, `. Server after-validation requires supplied effective positive text and ordered effective character objects to equal that projection, including x/y. Reject inconsistency rather than silently correcting one representation. Legacy requests with no metadata keep their exact existing behavior.
- Keep existing 3000-character effective shared/character/base bounds. Separately bound every raw metadata section and the full metadata structure, including hidden text. With 2 shared sections and at most 6 × 7 character sections, a 3000-character per-section limit already bounds raw text at 132,000 characters; UTF-8 bytes can be larger. Whether to impose a smaller aggregate raw-text budget is a design choice. Hidden sections must not become an unbounded side channel around request limits.
- A snapshot payload is a bounded, versioned list/bundle of classified section text, grouped sufficiently to distinguish multiple source characters. It intentionally excludes enabled flags, coordinates, seeds, model/settings, experiment identity and browser card IDs. Generation metadata and reusable snapshots therefore use related but distinct models.

Metadata is useful even when every section is empty/hidden, so do not exclude present metadata merely because its effective projection is blank. Generation still requires a nonblank base supplied by effective shared or style content; saving a prompt snapshot should not require valid generation settings or a nonblank generation base.

### Existing persistence and provider boundaries

| File / anchor | Repository fact and implication |
| --- | --- |
| `apps/api/src/novelai_api/generations.py:38` | CharacterPrompt has nonblank 1–3000 character prompt and independent strict finite/default-centered axes in 0.1–0.9. No need to broaden it for hidden workspace cards. |
| `apps/api/src/novelai_api/generations.py:86` | GenerationRequest owns flat effective shared/style/characters, auto mode and settings. Add metadata here so typed history and runs carry it naturally. |
| `apps/api/src/novelai_api/generations.py:112` | `base_prompt` composes style and shared only, preserving the old shared string exactly when style is blank. With an effective shared projection, its logic can remain unchanged. |
| `apps/api/src/novelai_api/generations.py:120` | Existing after-validator rejects blank/oversized base and unsupported models only when the effective character list is nonempty. Add metadata/projection consistency to this validation boundary. |
| `apps/api/src/novelai_api/generations.py:254` | JobStore writes the complete `parameters.model_dump_json()` into settings_json; denormalized positive/negative columns are the effective strings. No history table migration is needed for metadata. |
| `apps/api/src/novelai_api/generations.py:370` | History reload calls `GenerationRequest.model_validate(json.loads(settings_json))`. Optional absent metadata preserves every existing flat/native row. Valid present metadata returns hidden text to its authenticated owner. |
| `apps/api/src/novelai_api/generations.py:604` | Ordinary seed assignment uses `request.model_copy(update={"seed": seed})`; this is not a new prompt validation boundary and retains the nested metadata. The initial request must already be validated. |
| `apps/api/src/novelai_api/generations.py:637` | The provider receives the validated GenerationRequest. Hidden text is stored in the private request object but must never enter outbound arguments. |
| `apps/api/src/novelai_api/mcp_images.py:239` | Adapter builds an explicit allowlist of eleven effective flat arguments, using `parameters.base_prompt`. It does not forward model_dump or arbitrary metadata. |
| `apps/api/src/novelai_api/mcp_images.py:252` | Native support/count checks use only effective character_prompts; adapter iterates each effective CharacterPrompt and explicitly emits prompt/negative/enabled and manual axes, or no axes in automatic mode. This code need not gain section logic. |

The additive metadata approach preserves the useful boundary: source text stays lossless in workspace metadata while the provider only sees already validated effective strings. Adding blank/disabled characters directly to CharacterPrompt would propagate new semantics through model restrictions, provider counts, automatic positioning, native discovery and historical consumers without a provider need.

### All-hidden character mapping and validation cases

The metadata list and effective character list have different lengths. Build a projected list by iterating complete metadata characters in source order, composing each character's enabled text, and retaining only nonblank results **with the coordinates of that same source character**. Compare that final list with CharacterPrompt objects; never zip metadata against the already filtered effective list.

Example: metadata A has all sections hidden at `(0.2, 0.3)`; B has enabled `blue hair` at `(0.8, 0.7)`; C is an empty draft. The effective list is exactly `[{prompt: 'blue hair', x: 0.8, y: 0.7}]`. History/reuse restores A, B and C in order from metadata. B must not acquire A's coordinates or be displayed as the first source character. Automatic mode retains all metadata coordinates but the provider omits axes as before.

- Validate coordinates even for hidden/empty metadata characters; otherwise un-hiding a saved card introduces unvalidated placement.
- Validate a maximum of six metadata cards as well as the existing maximum of six effective cards.
- With zero effective characters the adapter stays on its existing eleven-field flat path; stored automatic mode does not require native capabilities when there is no actual character prompt.
- Nonblank hidden shared text does not satisfy base validation or the experiment's all-zero-style safeguard. Only effective shared text counts.
- Strict text/coordinate comparison rejects effective strings containing hidden content, missing enabled sections, reordered characters, duplicate projected entries, mismatched axes, and extra effective characters.
- Equality is a consistency guarantee, not a security boundary against an owner deliberately choosing text. API tests should prove correct filtering and no metadata forwarding at the real adapter boundary.
- The final design places the entire old shared/character string into its respective `其他` section, enabled, with other sections empty. Do not parse flat text to invent semantic classifications. Preserve the original raw string in that section; the one-part composition rule preserves legacy whitespace exactly.

### Frozen experiments, model_dump and same-ID compatibility

| File / anchor | Effect of additive metadata |
| --- | --- |
| `apps/api/src/novelai_api/style_experiments.py:27` | RunCreate contains GenerationRequest and rejects nested experiment identity. Metadata inherits validation through the nested request. |
| `apps/api/src/novelai_api/style_experiments.py:39` | `definition()` serializes the entire parameters dictionary with `model_dump(mode='json')`, normalized ranges and plan_version2. Present metadata freezes raw text, enabled state, original order and coordinates in definition_json. |
| `apps/api/src/novelai_api/style_experiments.py:83` | RunState reloads saved parameters through the typed nested model and retains legacy plan version privately. Optional absent metadata is compatible with existing definitions. |
| `apps/api/src/novelai_api/style_experiments.py:109` | Same-ID comparison removes plan_version, supplies only an omitted saved auto_character_position=false, then compares raw definition dictionaries. It must continue detecting changed enabled states, hidden text and any other definition keys. |
| `apps/api/src/novelai_api/style_experiments.py:291` | `group_parameters()` dumps run parameters, overrides style_prompt and seed, adds group ExperimentContext, then revalidates the complete GenerationRequest. Metadata covers shared/character sections only, so a style override leaves its projection consistent. |
| `apps/api/src/novelai_api/style_plan.py:256` | Style parsing remains exclusively on style_prompt. No section-specific parser change is required. |
| `apps/api/src/novelai_api/style_plan.py:311` | All-zero/base and length preflight reads effective positive_prompt. It remains correct if generation fields already contain the validated projection. |

**Important compatibility detail:** optional metadata with exclusion when None is smaller and safer than adding eagerly serialized empty lists/maps. For an old request, both model_dump and model_dump_json must omit prompt_sections entirely. Then old saved definitions and newly reconstructed metadata-free definitions compare identically with the existing narrow auto-mode normalization. No new `setdefault('prompt_sections', None)` is needed. Missing and explicit null input can canonicalize to the same omission; a present nonempty metadata object remains part of identity.

Do not replace the raw same-ID comparison with `GenerationRequest.model_validate(saved).model_dump()`: existing models ignore unknown fields by default, so doing so could discard unknown saved parameter/definition keys and falsely equate different definitions. Preserve raw saved definition bytes and plan_version1/2 behavior. A new section representation of the same flat effective text is still a changed frozen definition and should conflict for an already-used ID. Hidden text changes also conflict, even if the provider projection is identical.

The existing tests demonstrate the required standard: `tests/test_style_runs.py:265` rejects unknown version/other keys; `:287` checks missing mode normalization while preserving exact saved JSON bytes; `:328` checks mode changes in both directions. Extend these patterns to metadata omission/presence and enabled/hidden text changes.

Browser caveats at the freeze boundary:

- `apps/web/src/style-run-store.ts:115` currently clones parameters shallowly and clones each effective character. A new nested prompt_sections object needs a real nested copy or a request builder that allocates fully independent metadata before `start()`. Later draft edits/imports/hide toggles must not mutate the pending frozen definition.
- `apps/web/src/api.ts:152` manually validates run responses. It currently knows no metadata. Add the optional shape check without requiring it on old runs.
- `apps/web/src/StyleExperiment.tsx:48` currently checks `generation.draft.positive_prompt` directly for blank shared content. If the draft stores raw sections, that preflight must read the enabled projection. Backend `style_plan.py` already receives effective positive_prompt.
- `apps/web/src/store.ts:393` constructs effective parameters before the authoritative browser experiment preflight; preserve this path and its source-revision guard.

### Smallest durable private owner-scoped snapshot store

No prompt snapshot store exists. Existing owner-scoped jobs and durable run storage provide the patterns; snapshots should not be fake generation jobs, experiment runs or advice rows.

Recommended new module/table/API, as design proposals:

- `apps/api/src/novelai_api/prompt_snapshots.py`: typed immutable SnapshotCreate, classified/versioned payload, SnapshotSummary/Page/Detail, SnapshotStore. A separate small prompt-section model module is reasonable if sharing classifications avoids imports from snapshot storage into generation models; this is an organization choice, not required new architecture.
- `migrations/0004_prompt_snapshots.sql`: `prompt_snapshots(user_id REFERENCES users(id), id, name, payload_json, created_at, PRIMARY KEY(user_id,id))` and an owner/order index `(user_id, created_at DESC, id DESC)`. An updated_at column is unnecessary unless rename/update is explicitly included. Save creates an immutable named bundle; individual section Save is the same path with one payload entry.
- POST `/api/prompt-snapshots` saves one bounded bundle atomically. GET collection returns owner-only paginated summaries; GET `/{id}` returns its payload; DELETE `/{id}` is a small useful companion to prevent a permanently growing personal library. No generation/provider calls occur during save/import/delete. Rename/update is optional scope.
- A client UUID and same-owner/id/same-payload idempotency are useful for lost save responses, following RunStore's pattern, although snapshot creation is not paid and this is a product/implementation choice. Same id with changed content/name should conflict. Do not automatically retry unknown mutation outcomes with a fresh ID.
- Bundle entries contain text plus shared/character and fixed section classification; retain source character grouping when one bundle selects sections from multiple characters. The final design's `character_index` is snapshot-local source grouping only, not a promised original/destination draft index or identity. Global import maps it to an explicit current target card. Never serialize a browser-only target ID into durable API data. Composite PRIMARY KEY(user_id,id) allows the same UUID for different owners without disclosing foreign existence through save conflicts.
- Snapshots omit hidden/enabled state and x/y under the final product decision. Applying either append or replace changes text only and preserves target enabled state. Append/replace is selected locally for import and defaults to append. Empty replacement text may intentionally clear a section; do not reuse CharacterPrompt's nonblank restriction for reusable fragment text.
- Import can fetch several selected owner-only detail endpoints, validate/resolve all destinations, compose all changes, then commit one draft mutation. A separate bulk endpoint is not necessary for the smallest store. Bound selected count/combined payload and reject overflow or missing destinations before partial application. Do not silently truncate at six characters or drop sections.

Existing DB/auth/error conventions to reuse:

| Existing source | Contract |
| --- | --- |
| `apps/api/src/novelai_api/db.py:39` | Short-lived connection; write=True uses BEGIN IMMEDIATE, FK checks, busy timeout, commit/rollback. Enforce owner quota/idempotency checks and insert in the same write transaction if included. |
| `apps/api/src/novelai_api/db.py:59` | Explicit migration only, restrictive new DB and WAL/SHM modes; SQL migration scripts are packaged. Never call migrate from a snapshot constructor or schema generation. |
| `apps/api/src/novelai_api/db.py:108` | Verified exclusive private SQLite online backup automatically includes the new table. Do not invent a separate public/static snapshot directory or copy a live WAL database. |
| `apps/api/src/novelai_api/app.py:156` | All `/api/*` mutation methods automatically require the configured same HTTPS Origin; every API response gets Cache-Control:no-store. |
| `apps/api/src/novelai_api/app.py:168` | Routes require `Annotated[UserInfo, Depends(require_user)]`; derive ownership from that user, never request payload user_id. |
| `apps/api/src/novelai_api/app.py:352` | Existing owner/missing lookup returns generic 404. Snapshot queries must include both user_id and id, including deletion. |
| `apps/api/src/novelai_api/app.py:146` | Invalid body/query produces generic typed 422, sqlite3.Error produces safe 503/not_ready; no text/SQL details leak. |
| `apps/api/src/novelai_api/app.py:315` | Collection pagination uses limit default20, range1–100, JS-safe nonnegative offset, `limit+1` lookahead and next_offset. Snapshot summaries should exclude full text. |
| `apps/web/src/api.ts:264` | Central same-origin credentialed/no-store request wrapper handles mutation JSON and session-safe 401 reset. Add snapshot methods here. |

**Rate convention fact:** there is no shared CRUD rate limiter. `app.py:80` is a five-attempt login limiter keyed by client; `tags.py:179` is one concurrent upstream search; `advice.py:56` caps two paid advice turns; GenerationManager has its own queue/storage admission. Do not reuse these unrelated queues for local snapshot CRUD or claim snapshots already have rate protection. Fixed bounded payloads/pagination are necessary. If a per-owner snapshot count/total-size quota or write limiter is included, give it an explicit contract and perform quota admission transactionally; it is a new policy decision, not an existing repository requirement. The tracked Nginx snippet contains no snapshot-specific limit rule.

### Schema4 and rollout/fallback implications

Adding only generation metadata requires no migration; the independent durable library requires schema4.

Required affected anchors:

- `apps/api/src/novelai_api/db.py:12`: SCHEMA_VERSION 3 -> 4.
- `db.py:77`: append migration4 to the ordered explicit migration list.
- `db.py:95`: readiness must require version4 and probe the new table alongside existing tables.
- `apps/api/pyproject.toml:31`: package-data already includes `migrations/*.sql`, so no build-system change is needed for a new SQL file.
- `apps/api/src/novelai_api/admin.py:26`: existing migrate command delegates to Database; no new CLI command is needed for normal migration.
- `deploy/novelai-api.service:18`: tracked service example already runs the staged `novelai-admin migrate` before API startup. Application construction itself must remain side-effect-free.

Schema3's `Database.check_ready()` requires exactly version3 (`db.py:99`) and its migrate rejects a future version (`:75`). Therefore schema3 API code is not a valid recovery target after schema4. Follow the established durable-experiment deployment contract: verified private online backup and idle preflight; stop old API; migrate as service user using staged new code; verify schema4/integrity and preserved auth/history/run counts; start API; verify readiness and additive running OpenAPI; then switch the web. No credentials, provider semantics or Nginx topology changes are needed.

Keep the new compatible API/DB during a web fallback. Old web code can display and submit effective fields but cannot preserve the new hidden metadata or operate the snapshot library. A fallback UI therefore does not establish lossless section editing. Do not silently rewrite saved metadata through old reuse flows. Already-open new tabs still require new endpoints and metadata persistence. Prefer a forward fix; a DB restore/downgrade is a separate operator recovery decision that loses newer writes, never an automatic release rollback.

When using a backup clone for validation, do not start an active copied scheduler against configured live paid providers. Existing contract: `.trellis/spec/backend/deployment-contract.md:93` and `apps/api/tests/test_style_runs.py:924`.

### Affected consumer anchors: section targets, summaries, advice

| Consumer | Required review |
| --- | --- |
| `apps/web/src/store.ts:40` | PositiveTagTarget currently means style/shared/character ID. Extend it to shared section key or character stable ID + section key. Never use a filtered effective character index. |
| `store.ts:275` | Positive destination options/labels currently contain one shared and one per character. Generate an explicit destination for each new section; preserve style. |
| `store.ts:285` | Invalid target fallback currently goes to positive_prompt. Define one valid shared section fallback for removal/reset/reuse/import mappings. |
| `store.ts:315` | Character removal currently only invalidates exact `character:${id}`. All section targets belonging to the removed ID must invalidate. |
| `store.ts:321` | Tag insertion edits current text, trims joining separators and increments draftVersion. Resolve and edit only the chosen source section, preserving enabled state. |
| `store.ts:341` | Reuse currently reconstructs cards from effective character_prompts and resets the target. Prefer complete prompt_sections when present; only use legacy effective mapping when absent. Otherwise all-hidden cards and their source numbering disappear. |
| `store.ts:270` | Edit/generation revision invalidates pending entry restore. Hide toggles, snapshot imports and new section edits must also increment it. |
| `apps/web/src/App.tsx:353` | Tag tool selected label and selector derive from positiveTagTargets; App PromptEditor onFocus handlers around `:117`, `:122`, `:145` must pick exact section targets. |
| `apps/web/src/CharacterPositions.tsx:25` | Position markers use the full draft card list/stable IDs; retain metadata card coordinates rather than deriving markers from the filtered provider list. |
| `apps/web/src/PromptSummary.tsx:4` | Its narrow Pick type and rendering only show effective shared/characters. Add metadata-aware display so owners can inspect sections/hidden state and correct source character numbering; retain effective fallback for old rows. |
| `apps/web/src/App.tsx:339`, `:428` | Current-generation and history summaries share PromptSummary. |
| `apps/web/src/StyleExperiment.tsx:178` | Frozen experiment parameters share PromptSummary. |
| `apps/web/src/SavedResults.tsx:112` | Saved ordinary/experiment details share PromptSummary; no separate metadata parser should diverge here. |
| `apps/web/src/store.ts:846` | Protected reset clears existing stores. New snapshot library selection/loading/text and pending import results need the same session/epoch disposal rules. |

**Advice is currently independent and display-only.** `apps/web/src/App.tsx:391` renders an explicit advice input/output form, not a generation-field apply button. `store.ts:761` sends only trimmed AdviceStore.input, and `api.ts:357` sends `{input}`. Backend `advice.py:9` rejects extra input fields; `app.py:563` forwards only payload.input. The runner's `codex_advice.py:28` instructions and strict `suggestion` schema are display-only. The current spec explicitly says only submitted advice text reaches the model and no page state/history/snapshots are read (`.trellis/spec/backend/codex-advice-contract.md:24`).

Consequently section editing/snapshots alone require no advice API/runtime change. Do not automatically send new sections, hidden text or saved snapshots to recommendations. If later adding explicit copy/apply actions, that is a separate product change: exact target chosen by the user, text-only draft mutation, preserve hidden state, invalidate draft revision, and retain explicit submitted-input boundary. Existing regression is `apps/api/tests/test_advice.py:71` (`test_advice_requires_session_and_never_reads_page_state`).

### Implementation and meaningful offline test inventory

Proposed app changes: new `prompt_snapshots.py`, migration `0004_prompt_snapshots.sql`, optional shared `prompt_sections.py`; existing `generations.py`, `db.py`, `app.py`, checked-in `apps/api/contracts/openapi.json`; browser `api.ts`, `store.ts`, `style-run-store.ts`, PromptSummary/App/position consumers and a library store/view as chosen by implementer. The adapter and style-plan algorithms can remain unchanged under the additive effective-projection design, but their boundary regressions should prove that claim.

Meaningful backend checks for implementation (not run during this research):

- `apps/api/tests/test_generations.py:129`, `:188`, `:231`, `:275`: add mismatch/strict enabled/hidden text/bounds validation; metadata + effective fields round trip through owner history, restart and online backup; legacy no-metadata unchanged; all-hidden first/middle cards preserve later coordinates/order; no history/provider side effects for invalid projection.
- `apps/api/tests/test_mcp_images.py:499`, `:548`, `:661`, `:682`: exact effective payloads only, sentinel hidden text/metadata absent, flat eleven arguments for all-hidden characters, automatic/manual semantics and native gates unchanged. `:682` already proves experiment metadata does not change provider arguments.
- `apps/api/tests/test_style_runs.py:287`, `:343`, `:610`: optional absent metadata keeps old canonical same-ID definitions byte-identical; present metadata freezes all text/enabled/cards/coordinates; changed hidden state/text conflicts; restart preserves metadata without repeating an ordinal; group style override remains projection-consistent.
- `apps/api/tests/test_style_plan.py:162`: nonblank hidden shared text cannot rescue an all-zero style plan, while enabled shared projection does.
- New `apps/api/tests/test_prompt_snapshots.py`: authenticated owner save/list/detail/delete; foreign/missing generic404; wrong/missing Origin; fixed classification/shape/size/count bounds; one atomic named multi-section bundle; no enabled/settings/client IDs accepted or persisted; pagination; idempotency/conflict if adopted; survive restart/backup; no generation/provider invocation.
- `apps/api/tests/test_auth.py:165`, `:224` and `test_style_runs.py:898`: schema3->4 migration is idempotent; preserved sessions/jobs/runs/private modes; backup includes snapshots and no image bytes. Existing assertions hardcode version3 at `test_auth.py:253`, `test_style_runs.py:222`, `:917`; update current-version expectations deliberately while retaining genuine legacy-fixture version assertions.
- `apps/api/tests/test_api_contract.py:16`: add typed snapshot routes/error responses and optional metadata shape, intentionally update deterministic secret-free OpenAPI; schema generation must create neither DB nor files/provider work. Browser types and checkedRun must agree.
- Existing backend quality gate remains full offline pytest, Ruff and frozen dependency/lock checks under `.trellis/spec/backend/quality-guidelines.md`; do not claim a configured Python type checker. Frontend verification stays lint/types/source review and env-free build under the operator's no frontend/helper/browser tests rule.

## Files Found

The tables and test inventory above give exact paths, descriptions and source anchors for all affected files. Additional read-only context: `apps/api/src/novelai_api/migrations/0001_auth.sql`, `0002_generations.sql`, `0003_style_experiments.sql` establish the schema/FK pattern; `apps/api/tests/conftest.py` blocks live HTTP; `deploy/README.md` and `deploy/nginx-novelai.conf.example` establish private state and same-origin routing.

## Related Specs

- `.trellis/spec/backend/native-character-contract.md` — effective native bounds/mapping, stable IDs and additive history/rollout contracts.
- `.trellis/spec/backend/durable-experiment-contract.md` — complete frozen parameters, narrowly normalized same-ID identity, no replay and schema migration lifecycle.
- `.trellis/spec/backend/database-guidelines.md` — private DB modes, transactional explicit migration and online backup.
- `.trellis/spec/backend/api-contract.md` — owner-safe typed routes, no-store/safe errors, OpenAPI/browser synchronization.
- `.trellis/spec/backend/quality-guidelines.md` — offline fake providers, meaningful contract tests and required quality commands.
- `.trellis/spec/backend/codex-advice-contract.md` — explicit submitted input only, display-only suggestion and no advice SQLite storage.
- `.trellis/spec/backend/deployment-contract.md` — compatible API retention and private backup/idle/migrate/API-first publication patterns.
- `.trellis/spec/frontend/workspace-contract.md` — stable targets/reuse/session clearing, revision guards, controlled PromptEditor and no implicit advice state sharing.
- `.trellis/spec/frontend/style-experiment-contract.md` — frozen plan/settings and browser observer ownership.
- `.trellis/spec/guides/cross-layer-thinking-guide.md` — carry new fields through each writer/reader/consumer, rather than only adding request types.
- Active task `prd.md`, `design.md`, `implement.md`, `durable-experiment-design.md` — prior accepted boundaries; new section requirements arrive through the parent and need a follow-up design.

## External References / Versions

No external research or network access was needed or performed. Repository-declared runtime: Python >=3.12, FastAPI >=0.115,<1, Pydantic imported through the installed FastAPI stack, SQLite via Python sqlite3. The existing repository already uses Pydantic `exclude_if`, model_dump, model_validate and model_copy; this report relies on these source patterns rather than proposing a dependency upgrade. Advice pins `openai-codex-sdk==0.1.11` and `@openai/codex==0.152.1` (`apps/api/pyproject.toml`, `apps/api/package.json`); this feature does not require changing them.

## Caveats / Not Found

- This is source/spec research only. No app code, config, production state, credentials, .env files or git operations were touched; no tests, browser/helper automation, provider/network/paid calls were run.
- Exact contract choices are now frozen in `../prompt-sections-design.md`: metadata version1, fixed API names, snapshot-local character_index, POST201/client UUID idempotency and schema4 composite owner key. Additional quotas remain optional design policy. The final import append/replace/default and text-only snapshot semantics above are confirmed parent inputs.
- Existing specs contain older superseded deployment/provider statements; current native/durable contracts and the latest task follow-ups take precedence. Nothing in this research establishes real generated placement quality.
- No existing private snapshot library, general CRUD rate limiter or section-aware advice application path was found.
