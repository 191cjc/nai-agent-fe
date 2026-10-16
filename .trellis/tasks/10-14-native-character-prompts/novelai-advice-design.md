# NovelAI-aware advice

## Change boundary

The existing runtime INSTRUCTIONS only says image prompts/settings; section
consultation asks generic comma-separated prompt text. Strengthen the actual
model guidance in codex_advice.py INSTRUCTIONS and exact editable section seed
in SectionAssistant.tsx. Add a short visible NovelAI explanation to unified
advice in App.tsx. These are prompt/copy changes; no endpoint, metadata, runtime,
generation, billing, provider, database or dependency changes. Keep JSON schema
as the outer transport and plain tag text inside suggestion. No refactor.

## Common advice

Describe the task as NovelAI image prompt composition/optimization and relevant
generation settings. Prefer established English NovelAI/Danbooru-compatible
tags; translate intent expressed in Chinese to appropriate English tags.
Fallback short English descriptors are acceptable where no known tag exists;
do not claim live lookup/verification or guarantee every tag is canonical.
Preserve explicit meaning, requested section and subject. Do not invent or add
unrelated details. For prompt requests prefer concise comma-separated tags;
section-specific requests put only directly usable tags in suggestion, with
no heading/Markdown/explanation. Settings questions can retain concise helpful
explanations. Existing untrusted-user-text/no-tools/no-images/JSON restrictions
remain exact in force. No instruction to use tag search or other tools.

## Editable section scope

Use typed stable target.scope/section, not parsing display labels/person numbers.
Seed the visible consultation with NovelAI purpose, exact opening label, scope,
English comma-separated tag preference, output-only request and opening text.
Only this editable consultation is sent on explicit click; no hidden payload
or sibling context. Keep4000 input limit, safe truncation after prefix and all
existing popover/race/application semantics. Distinguish shared other vs person
other. Typed exhaustive maps/local helper may live in SectionAssistant.tsx;
no new general framework/module necessary.

| Target | Appropriate scope |
| --- | --- |
| Style | art style, medium, rendering/line/shading and requested visual treatment |
| Negative | unwanted content, visual defects/artifacts; exclusion tags |
| Shared scene | place, environment/background, time/weather, scene objects/lighting |
| Shared other | global framing/composition/perspective/mood and other shared details |
| Person character | identity/species/appearance/hair/eyes/facial/body traits |
| Person upper_clothing | upper garments, neckline/sleeves/material/color, upper accessories |
| Person lower_clothing | trousers/skirts/legwear/socks/shoes and lower accessories |
| Person action | pose/movement/gestures/body direction/expression/gaze/interactions |
| Person tags | supplementary descriptors for this person following current text/intent |
| Person special | requested special traits/local effects/special descriptions for this person |
| Person other | remaining local details for this person outside other sections |

Avoid imposing arbitrary content limits on ambiguous tags/special/other beyond
their local subject; user text can clarify their purpose. Ask for destination
relevance, not a promise that the model enforces taxonomy perfectly.

## Verification / publication

Use existing backend fake runtime/isolation tests, full frozen/offline suite,
Ruff/lock and unchanged OpenAPI. Do not add tests that simply match new literal
copy. Web lint/TypeScript and source inspection of all11 destinations, editable
input/context/limits, prior callbacks and unchanged paid boundaries. No frontend/
helper/browser tests or live paid advice/image probes. Parent syncs contracts,
fresh env-free exact-input build and scoped commit; stage matched schema4 API
and web using reviewed previous helpers adapted to fresh baseline. Private
backup, idle/recheck, config/image/expiry continuity, API-first readiness/public
hashes and old assets retained. No read-only balance probe needed for this
unrelated prompt change. Record evidence/journal; broader operator acceptance
remains open.
