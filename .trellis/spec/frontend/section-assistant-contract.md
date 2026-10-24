# Per-section AI Suggestions, Translation and Tag Search

## Scope / Trigger

Use for the prompt-section 助手 trigger/popover, local advice/search state,
exact prompt-target application and related AppStore/GenerationStore/API
wrapper lifecycle. Left unified advice and tag search remain independent.
The helper edits browser drafts only; existing server endpoints/schema4 and
image-provider adapters remain unchanged. Shared advice guidance follows the
backend [Codex Advice Contract](../backend/codex-advice-contract.md).

## Signatures

- `PromptTextTarget = SectionReference | {scope:'style'} | {scope:'negative'}`
  in prompt-sections.ts identifies an explicit style/negative field or shared
  section/stable person ID + section.
  Labels show current person number, but numbers never identify destinations.
- `SectionAssistantButton` and `SectionAssistantPopover` are shared UI in
  SectionAssistant.tsx. Editor owns one local opening and receives prompt
  drawer visibility; hidden panel/disclosure unmounts the portaled popover.
- `GenerationStore.assistantDraftRevision`, `promptTextAt(target)`,
  `invalidateAssistant()` and
  `applyPromptText(target,text,mode,openingRevision): void` own target identity,
  current value and atomic draft application. Invalidation is distinct from
  ordinary draft edits and occurs at reuse/reset/logout/disposal boundaries.
- `validateSectionBudgets(draft,target?)` preserves full validation by default
  for generation/snapshot import, while the assistant target limits validation
  to relevant prompt fields without coercing incomplete generation settings.
- POST /api/advice accepts only `{input: string}` (nonblank, max4000) and
  returns `{suggestion: string}` (nonblank, max3000). Existing auth/Origin and
  safe errors apply. Cancellation may use an optional AbortSignal wrapper
  argument; it does not change the wire contract.
- POST /api/tags/search accepts `{query: string, limit: 10}`. Use canonical
  candidate.tag as the applied value, not translated name or summary.
- Append and replace resolve the target in the generation store and validate
  a proposed string before writing it and incrementing the draft revision.
  No complete generation-request construction is required for a local edit.

## Contracts

Add the same compact helper to shared/person sections and style/negative
headings. One active compact popover escapes clipped prompt-drawer overflow,
anchors to its trigger and stays within the visual viewport. AI 建议, AI 翻译
and 提示词搜索 appear in that order and preserve their separate inputs/results
while switching within one opening.
Opening/switching has no network or generation side effect; close discards
local state. Existing section actions and style-experiment controls stay usable.

Opening AI leaves the requirement input empty. The operator types only their
own requirement; fixed NovelAI/tag guidance is added when explicitly submitting,
alongside the current label, typed destination scope and current section text.
Prefer established English NovelAI/Danbooru-compatible tags, comma-separated
and directly usable in that destination with no headings/Markdown/explanations.
Do not imply live tag lookup/verification. Resolve scopes from target.scope
and target.section, never translated labels/person numbering. Cover style,
negative, shared scene/other and all7 character sections; distinguish shared
global other from character-local other. For example upper_clothing requests
upper garments/sleeves/material/color, while action requests pose/expression/
gaze/interactions. Broad tags/special/other follow current text and intent.
Read the latest exact text from `generation.promptTextAt(target)` at submission,
including weights and comments; do not freeze context from the opening. Empty
section text is valid with a nonblank requirement. No other sections,
settings, images or advice history become implicit input. Show a short hint
that guidance/current section are automatically included. Only explicit
获取建议 assembles and sends the consultation. Validate the whole assembled
input against 4000 characters and show a local error without truncating context
or the requirement; click and Ctrl/Cmd+Enter share that guard. Default guidance
never becomes editable requirement text. Render returned suggestion as plain
editable text for user review, never markup/code, and apply only upon explicit
追加 or 覆盖. No automatic paid request, retry, tool operation or draft write.
Left unified advice continues using only its own consultation and display.

AI 翻译 explains the current exact section source in Chinese. Show the stable
target's latest promptTextAt value read-only, including weights/comment lines,
and an editable short question (up to500 characters). On explicit request,
freeze that source and build an input<=4000 from source/question/section label
and typed purpose, without silently truncating tags or reading other sections.
Empty source/question cannot submit. Translate original tags/visual effects,
explain relevant syntax, and acknowledge unknown terms without lookup claims.
The existing advice JSON envelope returns plain nonblank text<=3000; display
it with preserved line breaks and wrapping. Explanations have no append/replace
actions and never call applyPromptText or change the draft. If current source
changes during/after a request, mark/hide the older result and require an
explicit new request for current text. Translation owns independent local
request/error/loading/cooldown state via useLocalRequest, with all existing
opening/target/revision/session/visibility cleanup. Tab activation alone sends
nothing; Ctrl/Cmd+Enter is local and cannot submit generation. No chat history
or browser/server persistence is added.

Search has local query/results/errors/loading and Retry-After cooldown. Show
canonical tags, translations/NSFW/source and optional available metadata;
each candidate's explicit 追加/覆盖 edits the exact opening section. Do not
route through global positiveTagTarget or modify the left tag/advice stores.

Append preserves duplicate tags and existing source text, joining nonblank
parts with a comma plus newline using appendPromptText, so the new content
cannot join a final // comment line. Follow
[Individual Hidden Tags](../backend/prompt-comments-contract.md) for comment
compilation and source limits. Replace changes only the destination text. Both preserve
enabled/hidden flags, coordinates, sibling sections, settings and frozen run
definitions. Hidden sections remain editable without enabling them.
Check destination3000 and the relevant shared+style or person's composed3000
limits; negative text uses its own3000 limit. Do not block local editing on an
unrelated invalid field or missing model/sampler/seed/base. Failure is atomic
and visible in the helper, leaving draft content/revision intact.

Keep stable person targets and resolve again at Apply. Removal/reuse/reset
invalidates the opening; shared/style destinations also need draft identity
invalidation when the whole draft is replaced. An unrelated edit cannot
redirect a result. Latest target text is used at explicit application time.
Close/invalidate when opener disappears/is hidden, drawer/prompt panel hides,
session/logout/disposal changes or another helper opens. Abort requests where
supported, clear cooldown timers and reject late responses with identity/
epoch checks. Closing does not promise cancellation of an accepted server
advice turn and never causes an automatic retry.

Keep controls labelled, focus visible, tablist keyboard navigation local,
Escape/outside close and safe focus return. Escape must not propagate into
the underlying left-panel close handler. Inputs/Enter and button types cannot
submit the generation form. Helper controls use buttons/local key handling,
without a tool form; any future portaled form must also stop React submit
bubbling to the generation form. Bound the helper's own result scrolling and
reposition on viewport/scroll/mobile-keyboard changes without a hot loop.

## Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Open/helper tab switch | Zero network calls and draft edits |
| Explicit AI submit | User requirement plus fixed guidance and latest selected-section source only |
| Empty requirement / assembled input over 4000 | Local explanation and disabled submission; no truncation or request |
| Explicit translation | Current visible source/question only; read-only Chinese explanation |
| Source changes before/after translation response | Identify/hide old-source result; next request reads latest source |
| Search/AI candidate apply | Exact captured target, preserved hidden state |
| Missing/removed/reused/reset target | Close or reject; no fallback assignment |
| Oversized destination/relevant composition | Visible error; no partial edit |
| Incomplete generation settings/unrelated invalid field | Local valid edit remains allowed |
| Close/logout/disposal during request | Abort/invalidate; no stale result or draft write |
| Search rate limit | Show safe cooldown; no automatic repeated request |
| Escape/Enter in helper | Local close/tool submit; no underlying action |
| Narrow/short screen or drawer scroll | Bounded reachable popover and actions |

## Good / Base / Bad Cases

- Good: search for a pose from person2 action; change the left global target
  to person1, then append the result. Only person2 action changes.
- Good: hide lower clothing, append a searched tag and retain hidden state.
  It remains absent from the provider payload until explicitly shown.
- Base: empty/unconfigured draft can use the helper; advice/search errors are
  local and generation is still validated only upon Generate.
- Bad: a delayed suggestion writes into a newly reused shared prompt, a
  removed person silently falls back to a sibling, or Enter starts generation.

## Verification Required

Independent affected-frontend source review, npm run lint (ESLint/TypeScript),
whitespace/context validation and fresh env-free locked web build. Cover
stable targets/latest text/append-replace/length failure/incomplete settings,
hidden/reuse/import/session/request races, timer/abort cleanup, focus/keyboard,
drawer/tab/viewport behavior and unchanged generation/run/history flows.
No frontend/helper/browser automated tests or paid provider probes. A web-only
release verifies committed/build sources, exact public assets/health and old
hash retention with unchanged live API pointer/PID. Interaction and actual AI/
search content remain operator acceptance.

## Wrong vs Correct

- Wrong: modify global positiveTagTarget and reuse the left tool stores to
  apply a local result. Correct: capture an explicit stable target and keep
  independent assistant state with generation-owned validated writes.
- Wrong: send the entire generation request to advice on opening a popover,
  or insert its output on response. Correct: display an editable consultation
  and apply plain text only on the user's explicit action.
