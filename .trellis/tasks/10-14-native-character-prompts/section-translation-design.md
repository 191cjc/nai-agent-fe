# Per-section AI Translation (2026-10-20)

## Boundary

Add AI 翻译 immediately right of AI 建议 in each per-section assistant, before
提示词搜索. Explain current NovelAI prompts in Chinese without editing the
draft. The runtime currently requires English tags for section suggestions;
add an explicit translation/explanation exception to its fixed instructions.
Reuse POST /api/advice with its unchanged input/suggestion schema.

Product scope: SectionAssistant.tsx and necessary styles.css rules;
codex_advice.py INSTRUCTIONS only. No API/model/schema/dependency/runtime,
provider/database/generation changes, chat persistence or new tools. Existing
task, scoped commit and production publication authority applies.

## Frontend

- Tab order: advice, translation, search. Preserve keyboard tablist, local
  state across switches, portal bounds, focus and disclosure cleanup.
- Independent translation question/result/error/loading/cooldown state reuses
  useLocalRequest. Never share suggestion/application or left unified stores.
  Explanations have no append/replace actions and cannot mutate prompts.
- Show exact current section source read-only, resolved from the stable target
  with generation.promptTextAt(target), including hidden comments and weights.
  A short editable question defaults to concise Chinese meanings; users may
  ask about individual tags, weights or ambiguous phrases. No chat thread.
- Explicit 获取翻译 (or equivalent) / Ctrl-or-Cmd+Enter alone sends one request.
  Freeze source at click, building consultation from visible source/question,
  section label and typed purpose. No sibling/settings/image/advice context.
  Empty source/question blocks submission; input<=4000 without silent source
  truncation. A question limit around500 leaves room for3000 source characters.
- Request original-tag-to-Chinese meanings and visual effects, concise weight/
  // comment explanations and uncertainty for unknown tags; no invented tags
  or claim of live verification. Validate plain nonblank output<=3000.
- Render wrapped plain text, not HTML/executable Markdown or prompt content.
  If source changes during/after a request, mark the result as older or hide
  it with a retry hint; never label old meanings as current. Next explicit
  request uses current source. Tab activation alone performs no request.
- Existing revision/target/visibility/session guards and abort/epoch cleanup
  apply. Close/hide/logout/reuse/removal reject stale output. Enter and all
  translation controls cannot submit the enclosing generation form.

## Backend Instructions

Explicit translation/explanation requests about existing prompts receive
concise Chinese explanations inside the unchanged suggestion JSON field.
Identify original tags, explain meanings and mark ambiguity without adding
unrequested tags or claiming lookup. The English-tag-only rule applies to
composition suggestions. Keep JSON, untrusted-input/tool prohibitions,
runtime isolation/deadline/output bounds unchanged.

## Verification / Publication

Native implementers own disjoint frontend/backend files; independent full
affected-layer checker. Web ESLint/TypeScript/source review and fresh env-free
locked build. Backend existing fake-only full suite, frozen/lock/Ruff and
unchanged OpenAPI. No literal-copy tests, frontend/helper/browser automation,
live provider/AI/paid calls, token issuance or private image downloads.

Publish matched schema4 API first, then web, after private online backup and
zero-active-job/run gates. Preserve auth/rows/config/images/original expiry
and old releases/assets. Active work continues while API restart is deferred.
Exact staged/committed/build inputs and public hashes/readiness must match.
Model explanation quality remains operator acceptance; broader task stays
in_progress.
