# Per-section Assistant

## Boundary and Evidence

The section header currently has hide/save/import only (PromptSections.tsx).
App.tsx owns separate style/negative headings and the mounted left search and
advice tools. TagStore/AdviceStore use existing WorkspaceApi.search/advice;
these endpoint schemas are sufficient. Keep apps/api unchanged and publish a
web-only release without restarting API. This is an authorized follow-up to
the active editor task, rather than a new task/approval workflow.

Expected frontend changes: new reusable SectionAssistant.tsx and a small
state/helper module if useful; PromptSections.tsx/App.tsx integration;
GenerationStore/AppStore and WorkspaceApi only where needed for exact target
application, cancellation and protected lifecycle; styles.css for compact
responsive anchored popover. Avoid refactoring the unified tools.

## Interaction

Add a compact 助手 button to every shared/character section and style/negative
headings. One active anchored popover has two small tabs: AI 建议 / 提示词搜索.
Use a native top-layer popover with viewport-clamped positioning, or an
equivalent portal that escapes drawer overflow. Show the exact target label
(including person number) and keep bottom Generate/form behavior intact.

Opening and tab switching never requests advice/search. AI's editable input
is seeded from only the opening section label/text, within4000 characters,
with a concise request for directly usable comma-separated prompt tags. It
may be empty-section advice. Explicit 获取建议 invokes existing POST advice.
Show returned suggestion as editable plain text (max3000) with explicit 追加
and 覆盖 controls. User-visible text, never executable markup; no arbitrary
semantic extraction. Left advice remains unchanged and independent.

Search provides its own query/results/loading/error/rate-limit feedback using
existing POST tags/search. Keep canonical tag, translated name, NSFW and useful
optional metadata/source; each candidate has 追加 / 覆盖 for this target only.
Both tabs preserve state while switching within this opening. Closing clears
local assistant state; reopening starts fresh. No shared left tool-state use.

## Exact Target and Draft Writes

Represent target as existing SectionReference for shared/character or an
explicit style_prompt/negative_prompt kind. Never route through the mutable
global positiveTagTarget. Retain stable person IDs and resolve again at Apply.
Preserve enabled flags; hidden sections can be edited without enabling them.

The generation store owns an atomic apply method: copy the current section
draft, append nonblank raw text with ', ' or replace only target text; check
field3000 and relevant effective shared+style/character budgets and valid card
axes/count; commit exact destination text plus draftVersion only on success.
Do not require model/sampler/seed/nonblank base. No partial writes, settings/
coordinates/other sections/global target changes, deduplication or run edits.
Use the existing section budget helper, adding the negative-field limit where
appropriate. Keep errors visible in the popover rather than silently dropping.

Capture the draft's identity/reset/reuse revision separately from normal text
edits where needed. Removal/reuse/reset must invalidate an opening even for a
shared target whose key remains the same. Current target edits while a request
is pending do not receive an automatic overwrite; Apply always reads latest
text and validates it. Repeated intentional appends may retain duplicate tags.

## Lifecycle and Accessibility

One visible popover, no nested generation form or automatic request effects.
All action buttons type=button except independently portaled explicit tool
forms if used. Input Enter searches/requests only its intended tool and cannot
submit generation. Arrow/Home/End navigation stays local to tablist. Provide
labelled controls/status/errors, Escape/outside close, initial input focus and
return focus only to a connected visible opener or safe drawer fallback.

Keep the popover within visual viewport on resize/scroll and mobile keyboard;
bound its own result scroll. Close when opener is hidden/disconnected, prompt
drawer/prompt panel is hidden, parent section removed/reused, or session/logout/
disposal changes. Cancel pending fetch where supported and reject late state
updates with epochs/abort identity; never retry requests automatically. Existing
WorkspaceApi session handling remains authoritative. Local close cannot promise
server-side paid cancellation. Support Retry-After countdown without hot loops
or timers that survive close/reset. Do not disturb active server experiments.

## Verification and Rollout

Native implement agent owns frontend sources. Independent check covers all
changed web sources and specs, including stable-target application, hide/
import/reuse, all reset/session/close/request races, overflow and focus/Enter,
current search/advice independence and draft submission/run compatibility.
No frontend/helper/browser automated tests or paid probes. Run npm run lint,
fresh explicit22+ input env-free locked build, whitespace/context checks and
committed/build source equality. Backend source unchanged: no backend rerun.
Web-only stage/publication verifies exact public assets and retained previous
hashes, readiness/AIQQ and unchanged API pointer/PID. Do not restart API.
