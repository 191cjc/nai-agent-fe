# Prompt Sections and Reusable Snapshots

## Goal and Authorization

Extend the existing in-progress native prompt editor with the user's fixed
public/character sections, temporary exclusion, multi-section snapshots and
multi-snapshot import. The user selected configurable append/replace import,
defaulting to append. Existing implementation/deployment authority remains;
complete local checks and clean build before an idle/private-backup API-first
release. No paid probes, frontend/helper automated tests or browser automation.

## Product Behavior

- Public sections, in order: scene (场景), other (其他).
- Every independent character, in order: character (角色), upper_clothing
  (上半身服饰), lower_clothing (下半身服饰), action (动作), tags (标签),
  special (特殊), other (其他).
- Preserve PromptEditor's tag view, explicit manual edit and 0.1 weight
  controls, including neutral unwrapping. Each section has an accessible
  selection checkbox and upper-right 隐藏 / 保存 / 导入 actions.
- 隐藏 toggles participation rather than deleting text; show 显示/已隐藏
  state and retain the contents. Hidden content never enters effective
  generation prompts or MCP. History/reuse/entry restore retain all sections,
  hidden states, character order and coordinates, including all-hidden people.
- A composer toolbar exposes 保存所选 (one named snapshot for any selection
  of shared/character sections) and 导入快照 (multiple selections). Per-section
  save uses just that section; per-section import filters compatible source
  entries and targets that particular destination.
- Snapshots are private durable account data, survive refresh/restart and have
  no image-retention expiry. Snapshot text and classification are saved, not
  generation settings, image bytes or temporary enabled state. Import preserves
  existing destination enabled state. New characters start with enabled sections.
- Global import shows selected snapshot order and its affected sections before
  application. Shared entries return to their named shared sections; users map
  each snapshot character group to an existing character or a new one. No
  silent reassignment to a different character. All selected entries apply in
  the displayed selection order; repeated sections append by default, or the
  last selected entry wins in explicit replace mode. Preserve duplicate tags.
- Validate the whole proposed draft before applying it atomically. A missing
  target, >6 characters or text budget violation leaves the draft untouched.
  Appending joins nonblank source text with ', '; replacing affects only the
  imported sections. Keep all other text, positions, mode and settings.
- Snapshot save/import requires no valid model/sampler/seed and no nonblank
  generation base. Import checks prompt/section lengths, positions/card limits
  and targets atomically, but permits an incomplete draft. Complete generation
  validation remains at explicit submit; a person-only snapshot is useful
  before the scene/settings are filled.
- Old unsplit shared/character prompts restore verbatim in their respective
  其他 sections, enabled. No automatic semantic classification.
- Keep style/negative editors, experiments, main canvas, bottom generation
  controls, left drawers, auth, image ownership and uncertainty handling intact.
  Section edits do not mutate active server-run settings.

## Additive Generation Contract

Retain the current positive_prompt and CharacterPrompt list as the effective
provider payload. Do not relax legacy blank-character validation or teach MCP
about editor sections. Add this optional request metadata:

```text
PromptSection = {text: str(max_length=3000), enabled: strict bool=True}
SharedSections = {scene: PromptSection, other: PromptSection}
CharacterSections = {character, upper_clothing, lower_clothing, action,
                     tags, special, other: PromptSection}
SectionCharacter = {sections: CharacterSections, x: strict finite float=.5,
                    y: strict finite float=.5}  # .1 <= axes <= .9
PromptSections = {version: Literal[1], shared: SharedSections,
                  characters: list[SectionCharacter](max_length=6)}
GenerationRequest.prompt_sections: PromptSections | None = None
```

Use extra='forbid' for new metadata objects, strict boolean validation, explicit
fixed section fields and Field(default=None, exclude_if=lambda v: v is None).
Both model_dump(mode='json') and model_dump_json must omit absent metadata.
No character IDs belong in wire metadata. Preserve full metadata order/axes,
even when a person has no enabled nonblank text.

Composition collects enabled nonblank texts in the fixed order. No parts ->
''; one part -> original exact text; multiple -> trimmed texts joined with ', '.
Compose shared and every metadata character, then filter empty character
projections. The after-validator requires positive_prompt to exactly equal
shared composition and character_prompts to exactly equal the resulting ordered
nonempty {prompt,x,y} list. Existing active text lengths, base/model constraints,
coordinate checks and max6 remain authoritative. All individual metadata text
fields also retain their 3000-character bound. Mismatch is a 422 validation
error before seed/history/paid work.

This metadata is saved privately through existing settings_json. Actual MCP
mapping remains untouched and consumes only effective fields. A request with
all people hidden can have zero effective characters, preserving flat-model
compatibility while retaining hidden editor data. Existing callers/history
without metadata preserve original validation and serialization. Do not
rewrite stored old definitions or broadly normalize unknown keys. Existing
missing auto_character_position=false comparison is unchanged.

style_experiments.group_parameters copies/revalidates the full request and
changes only style/seed. Metadata excludes style, so it freezes naturally for
each group and remains consistent. Keep v1/v2 plan semantics and no-replay.

## Snapshot Browser API (Exact Shared Contract)

```text
SharedSnapshotEntry = {scope: 'shared', section: 'scene'|'other', text: str}
CharacterSnapshotEntry = {scope: 'character', character_index: strict int[0,5],
  section: 'character'|'upper_clothing'|'lower_clothing'|'action'|'tags'|
           'special'|'other', text: str}
PromptSnapshotEntry = discriminated union by scope
PromptSnapshotCreate = {id: UUID, name: str[1,100],
                        entries: list[PromptSnapshotEntry][1,44]}
PromptSnapshot = PromptSnapshotCreate + {created_at: int}
PromptSnapshotSummary = {id: UUID, name: str, created_at: int, entry_count: int}
PromptSnapshotPage = {items: list[PromptSnapshotSummary], next_offset: int|null}
```

All text max3000, new payload objects forbid extra fields. Name must be
nonblank; require at least one nonblank entry across a snapshot. Reject duplicate
(scope, character_index, section) keys. Shared entries forbid character_index;
character entries require it. Do not persist draft IDs or enabled states.

- GET /api/prompt-snapshots?limit=20&offset=0 -> 200 PromptSnapshotPage;
  limit1..100, offset nonnegative JS-safe, newest first with deterministic ID
  tie-break. Only this user's library. No raw storage path/content in summaries.
- POST /api/prompt-snapshots -> 201 PromptSnapshot. Client UUID plus exact
  canonical name/entries makes same-owner repeated same-ID save idempotent;
  changed content ->409/prompt_snapshot_conflict. Do not expose foreign IDs.
- GET /api/prompt-snapshots/{id} ->200 PromptSnapshot; foreign/missing ->404.
- DELETE /api/prompt-snapshots/{id} ->204; foreign/missing ->404.
- All use existing auth, same-origin mutation guard, safe ApiError and no-store
  middleware. Invalid shapes/queries422; no provider calls or job/seed side
  effects. Add documented errors and review OpenAPI intentionally.

Use schema4 migration0004_prompt_snapshots.sql for an owner/id-scoped table,
name/entries JSON/created_at and owner-order index. Wire Database migration list,
SCHEMA_VERSION and readiness table probe. Preserve token/session/job/run rows,
private permissions, image roots and online backup behavior. No disk files or
parallel storage system for snapshots. Existing old migrations remain intact.

## Frontend Owners and Data Flow

- New prompt-sections.ts owns fixed section keys/labels, typed composition,
  legacy restoration, selection references and atomic import projection. New
  browser wire types in api.ts must match the exact backend contract above.
- GenerationDraft owns shared_sections and each CharacterDraft.sections, with
  stable draft IDs and x/y. Remove flat draft text as a second editable source
  of truth; use typed helpers for effective display/request projections. Update
  all existing App/CharacterPositions/StyleExperiment consumers coherently.
- requestFromDraft includes effective fields plus independently copied full
  prompt_sections metadata. reuse/reset/entry restoration and all draft revision
  increments restore sections/hidden states without aliasing responses or runs.
- Positive tag insertion targets the precise enabled focused section. Update
  target picker labels, removal/hide/reuse/reset fallback, and keep style and
  negative insertion intact. No stale target may write to another character.
- A new PromptSnapshotStore under AppStore owns bounded paginated library/
  detail requests, save/delete and session epochs/abort handling. Clear all
  protected content on logout/401/dispose and never cache secrets or snapshots
  in localStorage. Saving/importing cannot submit generation forms or auto-run.
- New section/snapshot UI components may be extracted from App; do not create
  nested forms. Native dialog or established drawer controls must preserve focus,
  Escape/backdrop behavior, mounted prompt-editor state and responsive scrolling.
  Native buttons are type=button. Validate run metadata at the existing typed
  browser boundary; malformed new metadata must not become a paid draft.
- History/result PromptSummary displays fixed section names/enabled status
  when metadata exists, retaining legacy presentation otherwise. Do not label
  hidden characters/coordinates as generated content. Existing current/saved
  image navigation, active-run summaries and retention ownership stay intact.

## Ownership and Verification

1. Backend implementer owns apps/api source/models/routes/migration and meaningful
   offline regressions/OpenAPI. Frontend implementer owns apps/web sources and
   static lint/type checks. Both read this exact contract and notify parent of
   necessary contract deviations before making cross-owner edits. No nested
   agents, production operations, .env reads, browser/frontend/helper automated
   tests, paid calls, commits, push or amend. Parent owns specs/artifacts/release.
2. Independent full cross-layer checker reviews all sources and runs full
   offline backend frozen sync/pytest/Ruff/lock, web ESLint/TypeScript and exact
   OpenAPI. Cover hidden-text non-leakage with exact fake MCP payloads, fully
   hidden person index/position recovery, strict metadata mismatches, history/
   backup/restart/run freeze/idempotency, owner/Origin/no-store snapshot routes,
   schema3->4 preserving old records and privacy, idempotent/conflicting saves,
   malformed payloads/pagination. No Python type checker is configured.
3. Parent syncs executable contracts, creates fresh explicit env-free locked web
   build and scoped work commit, then stages matching committed API/web. Capture
   current baseline, verify idle and private schema3 online backup, gracefully
   stop, migrate4, preserve existing counts/config/private images, API-first
   readiness/OpenAPI then web publication, exact public and retained hashes,
   auth/no-store and neighboring health. Once schema4 commits, never restart
   old schema3 API or restore live DB; retain compatible new API on web fallback.
4. Record release evidence/journal; broad task stays in_progress for operator
   interaction/real-provider appearance acceptance.
