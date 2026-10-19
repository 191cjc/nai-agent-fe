# Individual Hidden Prompt Tags (2026-10-16)

## Boundary and authorization

The existing controlled strings and section metadata already preserve editor
source, but tags have no visibility and all raw strings reach generation.
Add individual hide/restore, whole-line comments and explicit blur formatting
in the shared editor/parser; compile comments at the API/provider boundary.
The user confirmed whole-line // comments and one tag per line on blur.
Existing task implementation, scoped commits and publication authority apply.
No new storage/schema/dependencies, paid probes or frontend/helper/browser tests.

Frontend ownership: apps/web/src prompt parser/editor, styles, request types,
sections/store and style experiment consumers. Backend ownership: apps/api/src
request/sections/compiler/style plan/provider, meaningful tests and reviewed
OpenAPI snapshot. Parent owns artifacts/spec synchronization/release. Preserve
other workers' edits. No nested implementation/check agents.

## Syntax and editing

A physical line whose first non-space/tab characters are // is fully hidden.
Inline // and URLs stay literal. If reflow or zero omission would promote an
inline marker to line-leading syntax, preserve the field/manual-only instead; escaped \// stays literal. CRLF/CR/LF work.
Do not strip or unescape literal active content. Hidden compilation removes
complete comment lines before composition, independently for each enabled
section. Keep surviving active source/newlines; no hidden tag can enter MCP.

Expose hidden chips with a mute style and accessible hide/restore controls.
Only the manual edit button opens the textarea. Hide/restore comments or
uncomments the selected occurrence; retain duplicate identity and body/weight.
Hidden tags can retain weight controls when their source mapping is safe.
Keep existing exact0.1/neutral1 behavior. On blur, reflow safely parsed tags to
one tag per line with comma separators between expressions (e.g. cat,\n// skirt,\ndog).
Every physical line of a safely supported multiline hidden expression must
be commented; never hide only its first line. Preserve internal grouped source
and escapes. Mixed active/commented or unsupported incomplete multiline scopes
remain intact/manual-only, with a clear hint instead of unsafe partial edits.
For the bounded first implementation, multiline expressions (including balanced
groups) remain original/manual-only for toggling and reflow. Single-line grouped
expressions still support visibility. Consecutive commented lines retain source
occurrence mapping; never treat a commented comma as an active separator. On any raw3000
expansion overflow keep the original input and expose an actionable error.
Merely mounting/viewing/reusing never formats or rewrites source.

Use one safe append helper for tag insertion, advice and snapshot append.
When both sources are nonempty join with a comma plus newline so appended
active or commented text starts on a separate physical line. Preserve source
and destination section enabled state, duplicates, atomic budgets and stale
assistant target/draft/session guards. No application can accidentally append
active text into an existing comment or concatenate sections before stripping.

## Additive request and persistence contract

GenerationRequest.prompt_comments is strict bool, defaults false, and is omitted
from both model_dump/model_dump_json when false. New editor requests send true.
Legacy missing/false uses exactly previous projection, provider and experiment
semantics; saved definitions/history are never rewritten in place.

Raw style_prompt/negative_prompt and raw section text remain persisted in the
existing settings_json. Metadata stays version1. Effective positive_prompt and
ordered character_prompts must match independent section compilation when
prompt_comments=true. No metadata requests compile their direct prompt fields
at the provider boundary too. Filter fully commented characters while keeping
source metadata/coordinates; model restrictions use effective characters.
Base and effective lengths/nonblank are checked before seed/history/provider.
Raw fields remain bounded3000. No flag, source metadata, comments or hidden
text is added to the explicit provider argument allowlist. Negative and all
flat/manual/automatic character paths use effective values. Avoid compiling
an already composed effective section value a second time if that could alter
literal content. History/snapshots retain raw comment source exactly.

Browser saved-record validation selects composition by saved flag (absent is
legacy). Restoration copies raw metadata/source. Subsequent explicit new editor
submission opts into comments; do not mutate frozen old requests or runs.
The flag is optional in wire types and frozen by request copying.

## Experiments

Keep plan_version1/2; frozen prompt_comments selects syntax independently.
Legacy parse/render/zero semantics remain exact. Modern browser and Python
must agree on occurrence indexes including hidden chips; hidden/manual-only
entries cannot be selected, varied or satisfy nonblank/all-zero survivor checks.
Zero removes only selected active occurrence, preserving other hidden source
and duplicates. Length checks account for raw source and effective combined
text conservatively; hidden source remains bounded. Same-ID changed flag or
hidden source conflicts; do not broaden canonical identity normalization.
Legacy absent/false definitions remain byte-identical and resume without replay.
No retries, seed, detach/reattach, Stop or retention changes.

## Validation and rollout

Meaningful fake-only backend regressions prove syntax/compiler, strict flag,
per-section filtering and coordinate order, raw history/snapshot restoration,
actual MCP argument exclusion (flat/manual/automatic), all-hidden rejection,
new experiment candidates/zero survivors and legacy frozen identity/restart.
Golden vectors cover CRLF, duplicates, URLs/escapes, weights, grouped/unknown
syntax and cross-language index policy. No live provider calls.
Full frozen pytest/Ruff/lock/OpenAPI; frontend lint/TypeScript/source review and
fresh env-free production build. Independent full affected-layer checker.

API-first deployment after fresh idle/private-online-backup/config/image gates.
Never interrupt active jobs/runs; wait if busy. Keep compatible API on web
fallback: old APIs ignore the flag and may leak hidden source to generation.
No automatic database restore or old-API downgrade after flagged writes.
