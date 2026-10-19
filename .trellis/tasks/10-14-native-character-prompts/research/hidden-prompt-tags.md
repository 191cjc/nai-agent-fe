# Research: Hidden prompt tags and line comments

- Query: Add per-tag hide/restore using `//` line comments, automatically format
  parsed tags/expressions on blur, preserve source in history/snapshots, exclude
  hidden content from generation and style experiments, and preserve old runs.
- Scope: internal source/spec inspection only; no product edits, test execution,
  external/provider/production access, credentials or `.env.local` reads.
- Date: 2026-10-16

## Findings

### Confirmed requirement and smallest reliable boundary

The parent reports that the user explicitly chose line comments: a line whose
first non-whitespace characters are `//` is hidden in full. Blur should format
one parsed tag/expression per line. A comma inside the commented line does not
reactivate later text on that line.

The smallest additive version boundary is a strict request boolean such as
`prompt_comments`, default false, omitted from serialization when false. New
browser submissions opt in with true. Keep old absent/false requests, saved
history and frozen v1/v2 runs on the current exact grammar. Do not globally
change the meaning of existing `//` strings.

No database migration is necessary: existing generation `settings_json`, run
`definition_json`, section text and snapshot `entries_json` can retain raw
commented source. Keep SQLite schema4. In the proposed minimal design, raw
style/negative fields already provide their own source storage; section raw
texts remain in optional `prompt_sections` metadata, with effective shared and
character values projected separately. Document that style/negative are raw
editor source in opted-in requests and compile them at their effective boundary.

This syntax flag can version comments independently of `plan_version`: keep
plan_version2's existing zero-omission semantics and gate comment parsing on the
frozen request flag. A new plan_version3 is unnecessary unless the weight/zero
renderer itself changes. Persist the flag with each new frozen run. Do not
normalize old absent mode to true during same-ID comparison.

An alternative is new private source metadata containing raw style/negative
and version2 section metadata, while all effective fields remain unchanged.
That has a cleaner exclusively-effective public prompt boundary, but adds
several source-field projections and requires synchronizing overridden style
source metadata in every experiment group. It is larger than the explicit flag
for this codebase; never combine these approaches accidentally.

### Files found and existing patterns

| File | Relevant existing responsibility |
| --- | --- |
| `apps/web/src/PromptEditor.tsx:16` | Shared editor for style, negative and every section; manual editing, chip view and exact0.1 controls. |
| `apps/web/src/PromptEditor.tsx:47` | Current blur only captures height and switches view; it does not rewrite text. |
| `apps/web/src/prompt-weights.ts:74` | Source-range tokenizer protecting escaped and balanced scopes and unsupported emphasis. |
| `apps/web/src/prompt-weights.ts:160` | Exact decimal adjustment, stale-source guard and1.0 outer unwrap. |
| `apps/web/src/prompt-sections.ts:44` | Single shared/character composition implementation. |
| `apps/web/src/prompt-sections.ts:100` | Strict response projection check used for saved history/run acceptance. |
| `apps/web/src/prompt-sections.ts:134` | Snapshots capture raw section text, including whole-section hidden text. |
| `apps/web/src/prompt-sections.ts:175` | Atomic multi-snapshot append/replace, destination enabled-state preservation and budgets. |
| `apps/web/src/store.ts:87` | Ordinary and experiment `requestFromDraft` preflight, effective native people and private metadata. |
| `apps/web/src/store.ts:323` | Assistant targeted append/replace with independent validation and revisions. |
| `apps/web/src/store.ts:377` | Left tag-search insertion; currently appends a comma on the last line. |
| `apps/web/src/store.ts:401` | History restoration and latest-entry restoration share raw style/negative plus restored metadata. |
| `apps/web/src/store.ts:451` | Experiment start freezes one request and occurrence-based ranges. |
| `apps/web/src/StyleExperiment.tsx:35` | Draft and frozen style source selector, occurrence checkboxes and previews. |
| `apps/web/src/style-experiment.ts:56` | Browser exact plan/count/length preview and source-offset edits. |
| `apps/web/src/api.ts:35` | Shared browser request type; `checkedRun` and history validation at163/192. |
| `apps/web/src/PromptSummary.tsx:5` | History/source-numbered section summaries and generated-person status. |
| `apps/api/src/novelai_api/generations.py:87` | Typed request and base/metadata/native-model preflight. |
| `apps/api/src/novelai_api/generations.py:265` | Existing private job columns plus complete `settings_json` storage. |
| `apps/api/src/novelai_api/generations.py:381` | History revalidates saved request JSON with current model. |
| `apps/api/src/novelai_api/prompt_sections.py:28` | Private section projection; presently exact single text or trimmed comma join. |
| `apps/api/src/novelai_api/style_plan.py:75` | Python port of source-preserving browser tokenizer; currently imports GenerationRequest. |
| `apps/api/src/novelai_api/style_plan.py:238` | Current source-based plan, decimal dimensions, zero omission and maximum lengths. |
| `apps/api/src/novelai_api/style_experiments.py:39` | Canonical run definition; plan_version2 plus full request and normalized ranges. |
| `apps/api/src/novelai_api/style_experiments.py:101` | Same-ID raw definition comparison; only omitted auto-position false is normalized. |
| `apps/api/src/novelai_api/style_experiments.py:291` | Every group revalidates overridden style/seed against the frozen request metadata. |
| `apps/api/src/novelai_api/mcp_images.py:239` | Explicit provider allowlist; base, negative and ordered native-person arguments. |
| `apps/api/src/novelai_api/prompt_snapshots.py:38` | Immutable owner-scoped raw-text snapshot validation/storage, no provider work. |

### Compiler/parser contracts to freeze before implementation

1. Define line endings identically in TypeScript and Python: LF, CRLF and lone
   CR. Do not use differing default Unicode `splitlines` behavior. Existing
   tokenizer recognizes comma/LF/CR only and Python explicitly mirrors JS
   whitespace (`style_plan.py:16`). Preserve that parity.
2. Recognize `//` only at the first non-whitespace position of a physical line.
   URLs such as `https://...`, interior `tag // text`, and escaped markers must
   not become an incidental inline-comment feature. Decide/document literal
   line-leading markers; retaining a backslash escape unchanged is safer than
   an unescape operation that makes compilation non-idempotent.
3. Compile each enabled section independently, then compose its effective
   content. Never raw-join sections then strip comments: a trailing comment in
   one section could swallow the next section. Whole-section disabled state
   wins regardless of tag flags, without mutating its raw source.
4. Pure-comment source is effective empty. It cannot satisfy ordinary base
   validation or all-zero experiment preflight. Comment-only native people
   must be omitted by metadata projection, preserving the correct source axes
   and numbering of surviving people. Keep existing strict nonblank effective
   CharacterPrompt validation rather than weakening it globally.
5. Preserve separators at comment deletion boundaries. `a\n// b\nc` must not
   become `ac`. Blur may canonically emit comma/newline separators between
   top-level expressions; it must not raw-split commas inside weights,
   brackets, escaped commas or incomplete scopes.
6. Keep original expression bodies, escapes, duplicate occurrences and weights.
   Decimal math remains scaled integer, ordinary0.0 emphasis remains distinct
   from experiment selected-zero omission, and1.0 unwraps only the supported
   outer numeric group. Never change unsupported syntax to guessed tags.
7. Tag source ranges/weight ranges must refer to the exact raw source used by
   the edit. Comment-prefix removal requires an offset mapping or explicit
   retained raw spans; virtual string offsets cannot index raw strings. Keep
   stale-range checks. Python/JS offsets differ for astral Unicode, so the wire
   continues to use occurrence indexes rather than character offsets.
8. The normal editor can include hidden chips with restore controls. Experiments
   must reject hidden selections and use one frozen, explicitly defined index
   space (all displayed occurrences with hidden disabled, or active occurrences
   only). Browser, server, weights metadata and zero omission must agree.
   Filtering and then reusing original zero-omission index assumptions is unsafe.

### Multiline groups and malformed source

Balanced numeric/bracketed expressions may contain physical newlines. They are
one parser expression, not several independently toggleable tags. Do not flatten
their internal newlines, split them on commas, or prefix only their first line.
For whole-expression hide, add `// ` to every physical line; restore removes
exactly one generated marker per physical line and keeps the body untouched.

A practical parser can parse contiguous commented blocks after removing their
line markers and map virtual ranges back to raw spans. This recovers a multiline
weighted hidden expression as one restorable chip and handles adjacent hidden
tags separated by retained commas. If an expression spans mixed active and
commented physical lines, preserve that raw expression and make reflow/toggle
manual-only rather than guessing how to regroup it. The active compiler can
still apply explicit whole-line comment semantics before active parsing.

Unknown/incomplete expressions should retain original raw bodies and disabled
weight controls. Formatting should not invent delimiters or closing scopes.
If reliable multiline block mapping is too large, a manual-only exception for
multiline/ambiguous expressions is safer than a partial-line toggle, but the
parent must decide whether that UX limitation satisfies the requirement.

### Insertion, formatting and length hazards

All current insertion paths can accidentally hide newly appended content:

- `store.ts:328`: section AI/search assistant appends with `', '`.
- `store.ts:377`: left search trims the last comma and appends `', tag'`.
- `prompt-sections.ts:209`: snapshot append joins section texts with `', '`.
- `prompt-sections.ts:44`: raw section composition joins with `', '`.

Use one syntax-aware append helper that inserts a new line boundary when the
last source line is commented; retaining `,\n` between expressions consistently
is also viable. Preserve duplicate tags and explicit replace semantics. Import
must remain atomic and retain destination section enabled state. Replacement
and assistant output still need blur-independent correct compilation.

Raw max3000 applies before provider compilation, including comment prefixes,
commas/newlines, and generated weight wrappers. Formatting `a,b` to `a,\nb`
already adds a character; hide adds markers. Do not truncate source. If a
format/toggle would exceed the budget, keep the original source and show a local
actionable error. Preserve pending click position/textarea height behavior on
blur. Editor text changes must update existing draft revision guards so latest
history cannot overwrite a newly formatted/manual edit.

Experiment maximum-length/preflight has two budgets in opted-in mode: bounded
raw source, and effective composed base. Commented text cannot count as an
unselected surviving style tag or shared base. Reusing a raw style length minus
trim formula without comment-aware bounds can falsely reject or accept plans.
Zero omission must preserve hidden raw source needed by history, even when no
active style tags survive; its current all-tags-removed=>empty-string rule
cannot simply be applied to a mixed raw hidden/active tag list.

### Persistence and compatibility

Existing JobStore writes the entire validated request to `settings_json` and
revalidates it on read. Additive omitted-false mode is enough to preserve old
saved bytes and grammar. Snapshots already preserve raw source unchanged;
hidden tag flags survive as `//` text. They intentionally do not save the
whole-section enabled flag (`PromptSections.tsx:73` wording may need to
distinguish this from tag comments).

Old snapshots do not carry a syntax version. Importing them into the new editor
or explicitly resubmitting restored old history can interpret literal leading
`//` as comments. The parent proposal accepts new editor syntax on the next
explicit submit without rewriting persisted history. If exact old literal-tag
semantics must also survive reuse/import, add snapshot syntax metadata or an
explicit lossless legacy-to-new conversion; never quietly claim both behaviors.

Old frozen runs must retain missing/false comment mode, old parser indexes,
old max-length calculations and byte-identical `definition_json`, even after
restart. Changed new hidden source or true/false mode conflicts on same ID.
Existing source/cursor/claim/recovery/idempotency guarantees must be unaffected.

API-first rollout is required because older APIs ignore unknown request fields
and would forward raw `//` style/negative text or reject section projection.
Retain the compatible API on frontend fallback; unchanged SQLite schema does
not make downgraded request/history readers safe. No provider calls or new
automatic submission behavior are needed for acceptance checks.

### Existing tests/golden vectors and meaningful additions

- `tests/test_style_plan.py:24` golden vectors already cover escaped comma,
  CR/LF, trailing escape, literal colon, unknown scope, nested weights/brackets,
  JS whitespace parity and source-slice invariants. Tests at64/78 cover duplicate
  occurrences and astral Unicode;119+ covers exact zero removals and separator
  runs;190+ covers plan_version1 zero behavior. Keep all unchanged-mode vectors.
- `tests/test_prompt_sections.py:152` rejects invalid metadata version/keys;
  existing history/provider/frozen-run tests prove hidden whole sections never
  reach MCP and retain source axes. Extend with raw comments, mismatched
  comment-mode projection and comment-only source people/shared sections.
- `tests/test_style_runs.py:286` covers absent old auto-mode, exact raw
  definition preservation and versions absent/1/2. Add old literal`//` v1/v2
  reattachment/restart/next-group vectors, omitted-false serialization and
  same-ID syntax/source conflicts. New comment-aware runs must continue after
  failures and use the same frozen seed, without ordinal replay.
- `tests/test_mcp_images.py` should assert exact flat/manual/auto payloads with
  opted-in raw commented style/negative/character source, and prove neither
  comments nor private editor flag/metadata enter arguments. Keep the paid-call
  allowlist and no-retry behavior untouched.
- `tests/test_prompt_snapshots.py` can prove comment source is stored/retrieved
  verbatim, idempotent/private and survives backup/restart. No schema migration
  test changes are necessary merely for raw text content.
- Add backend shared golden examples for indented markers, inline non-markers,
  URLs/escaped markers, blank/comment-only lines, CRLF/loneCR, hidden duplicate,
  grouped numeric/legacy syntax, balanced multiline hide/restore, malformed
  multiline preservation, active tag adjacency across hidden lines, all-zero
  plans with only hidden remainder, raw/effective near-limit strings and hidden
  index rejection. Use fake providers/disposable data only.
- Review OpenAPI additive strict mode in `contracts/openapi.json` together with
  `api.ts`, checked history/run guards and PromptSummary source/participation
  wording. Follow project prohibition on frontend/helper/browser automated
  tests: ESLint, TypeScript, source review and clean env-free build only.

### Related specs and external references

- `.trellis/spec/backend/prompt-sections-contract.md`: raw editor metadata,
  exact effective projection, source-person coordinates, immutable snapshots,
  atomic import and old missing metadata/definition compatibility.
- `.trellis/spec/backend/native-character-contract.md`: base bounds, effective
  nonblank people, provider allowlist, history JSON and API-first compatibility.
- `.trellis/spec/backend/durable-experiment-contract.md` and
  `.trellis/spec/frontend/style-experiment-contract.md`: frozen Cartesian
  occurrence semantics, no paid replay, zero omission and legacy renderer.
- `.trellis/spec/backend/api-contract.md`: deterministic additive OpenAPI,
  authenticated safe browser boundary.
- `.trellis/spec/backend/quality-guidelines.md`: full fake-only backend suite,
  Ruff/frozen lock, no credentials or paid probes in tests.
- `.trellis/spec/guides/index.md`: search before new helpers and trace data
  transformations across layers. Existing tokenizer should be reused rather
  than introducing a naive comma splitter.
- External references: none needed or accessed. `//` is a workspace editor
  feature, not a claimed NovelAI upstream comment syntax; it must be compiled
  away before MCP submission.

## Caveats / Not Found

- Current source has no comment support or individual tag visibility state.
- Research does not establish how NovelAI would interpret raw comments; no
  provider/paid call was made, and raw comments must not reach that boundary.
- Exact new field/function names, ambiguous multiline fallback, legacy snapshot
  reuse policy and experiment index-space choice belong to the parent's final
  design. No product/spec/git files were changed by this researcher.
