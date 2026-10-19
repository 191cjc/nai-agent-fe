# Individual Hidden Prompt Tags

## Scope / Trigger

Read when modifying prompt parsing/editing, section projections, generated
provider arguments, history/snapshot recovery or frozen style plans. This is
workspace syntax, compiled before NovelAI; it is not provider comment syntax.
Raw editor source and effective generation text have separate responsibilities.

## Signatures

- `GenerationRequest.prompt_comments: strict bool = False`. False is omitted
  from `model_dump()` and `model_dump_json()`; modern editor requests send true.
- Raw `style_prompt`, `negative_prompt` and `prompt_sections` text remain in
  existing private saved JSON. Metadata remains version1; SQLite stays schema4.
- `compile_prompt_comments(source: str) -> str` removes complete comment lines.
  GenerationRequest exposes effective style, shared, negative and characters;
  provider arguments use only these effective projections.
- Section composition accepts syntax mode and compiles each enabled source
  independently before joining. Absent/false mode uses the exact legacy path.
- Browser `parsePromptTags(source, comments=false)` and Python
  `parse_prompt_tags(source, *, prompt_comments=False)` preserve legacy defaults.
  New editor/plan calls opt in; stored-run viewers use the saved flag.
- `createStyleExperimentPlan(source, ranges, comments=true)` computes raw and
  effective maximum lengths without materializing combinations.
- Frozen request mode selects syntax independently of internal plan_version1/2.
  The wire still identifies tag occurrences by index, never JS/Python offsets.

## Contracts

A physical LF, CRLF or CR line is hidden when its first non-space/tab characters
are `//`. The entire line is hidden, including comma-separated text on that line.
Inline markers, URLs and escaped line-leading markers remain literal. If
reflow/zero removal would promote an inline marker to comment syntax, retain
the field as manual-only. Do not
unescape active source; compilation preserves surviving content and line endings.
Never raw-join sections before removing comments, or append active text onto a
commented last line. Search, advice and snapshot append share a comma+newline
boundary when both sources are nonempty.

The controlled raw string remains the source of truth. Hidden chips remain
visible and recoverable with accessible hide/restore buttons; preserve body,
weights and duplicate occurrence identity. Any multiline/manual-only expression keeps its field from automatic reflow
and visibility toggles; supported independent weights remain available. Hidden
chips keep their weight but must be restored before adjustment; single-line grouped expressions remain
supported. Unknown syntax is retained, never guessed or silently repaired.
Only the manual-edit button reopens text mode. Explicit textarea blur formats
safe expressions one per line with comma/newline delimiters and `//` markers.
Mount/view/reuse does not format. Preserve the old textarea height and pending
click position; guard raw3000 limits for blur, hide/restore and weight changes.
On overflow preserve original source and show an error, never truncate.

History and snapshots preserve raw comments. Whole-section hiding still wins.
Effective all-comment people are filtered without losing source coordinates or
transferring them to another person. Fully hidden base cannot satisfy nonblank
validation; enforce effective lengths before seed/history/provider. Metadata
projections must exactly match effective fields. The MCP allowlist never gains
raw metadata, comment flags or hidden source; negative/flat/manual/automatic
paths all use effective text.

Modern experiment indexes include hidden entries, but hidden/manual-only entries
cannot be selected or varied. Hidden text cannot satisfy all-zero survivor or
shared-base checks. Selected zero removes only that active occurrence, retaining
unselected duplicates and hidden raw source. Browser/Python parsers and length
bounds agree. Old absent/false requests and saved runs keep exact old grammar,
zero version and definition bytes; do not rewrite/replay them or broaden same-ID
normalization. Changed flag or hidden source conflicts. Reuse/import copies raw
source; only a subsequent explicit new editor submission opts into new syntax.

API-first publication is required even at unchanged schema4. Older APIs ignore
the flag and may submit hidden source. Keep the compatible modern API on web
fallback, including after accepting flagged history/runs. No automatic database
restore or unsafe API downgrade.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Flag absent/false | Exact legacy validation, serialization and frozen grammar |
| Flag true | Effective compilation; raw persistence |
| Flag string/number/null | 422 before side effects |
| All base lines commented | Reject before seed/history/provider |
| All source characters commented | Empty effective list; source cards remain recoverable |
| Section/effective text or ordered coordinates disagree | 422 before side effects |
| Blur/toggle/weight expansion exceeds3000 | Retain original text and show local error |
| Hidden/manual-only experiment selection | Reject before create |
| Reachable zero leaves only hidden style and no shared | Reject before create |
| Same run ID changed comment mode/source | Conflict; no duplicate work |
| Older frozen literal `//` | Preserve original literal interpretation and definition |

## Good / Base / Bad Cases

- Good: `cat,\n// red skirt,\nblue eyes` keeps the skirt in editor/history but
  excludes it from actual MCP text. Adding advice starts a separate line.
- Base: an old absent-flag run containing literal `//` resumes with its original
  parser and no replay. Explicitly creating a new editor request opts in.
- Bad: remove only the chip visually, comment only the first line of a grouped
  expression, or strip comments after concatenating raw sections.

## Tests Required

Fake-only backend tests cover strict flag/omission, CR/LF/CRLF and escapes/URLs,
per-section projection/coordinate order, raw history/snapshot recovery and exact
MCP argument exclusion for flat/manual/automatic paths. Assert modern hidden
candidate rejection, active-zero source preservation, hidden-only empty bases,
near-limit bounds and legacy frozen identity/restart without paid replay.

Follow full backend frozen sync/pytest/Ruff/lock and exact reviewed OpenAPI.
Web/helper/browser automated tests remain prohibited by operator preference;
use web ESLint/TypeScript, source review and fresh explicit env-free build.
Actual interaction/image appearance remains operator acceptance.

## Wrong vs Correct

- Wrong: append `, new_tag` after `// hidden`, or compile joined raw sections.
  Correct: append across a newline and compile each source before composition.
- Wrong: reinterpret all old `//` records globally or downgrade based on schema
  number alone. Correct: freeze explicit syntax mode and keep compatible readers.
