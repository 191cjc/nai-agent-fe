# Research: Codex tool isolation for advice

- Query: Can AiQQ's pinned Python Codex SDK and CLI/app-server provably deny **all** tools for advice, using only offline static evidence and non-billable negative tests?
- Scope: mixed (local AiQQ sources and official OpenAI documentation)
- Date: 2026-09-23

## Product Decision (2026-09-24)

The operator explicitly accepted AiQQ-equivalent restricted Codex execution
instead of demanding proof that every tool is unavailable before execution.
The findings below remain accurate for the original stricter question, but
their recommendation to leave the runner disabled is superseded by this
decision. Implement fresh isolated work/runtime directories, read-only
sandbox, network and approvals off, named capability switches off, and
fail-closed observed tool-event handling. Do not describe this as absolute
no-tools enforcement; side effects before an event cannot be ruled out.
Automated tests still use fakes and never call paid endpoints.

## Implementation Observation (2026-09-24)

With the pinned CLI 0.152.1, an offline feature probe reported
`unified_exec=true` even when `features.unified_exec=false` was requested;
`shell_tool` reported disabled. The adapter rejects observed tool events and
closes the SDK execution before deleting its temporary workspace. A fake
event test caught that aborting the SDK signal alone left its CLI process
running; explicit execution closure was added. Neither protection proves a
tool cannot act before its event reaches the adapter. Real model behavior
was not probed, and no paid request was made.

## Findings

- **Original strict-gate verdict: NO.** No complete no-tools negative test is established purely offline for this pinned SDK/CLI. The unresolved strict gate was **pre-execution enforcement**: prove that a real advice turn neither exposes any built-in/optional tool to the model nor executes a model-requested tool (including read-only shell), under the exact deployed CLI/version/configuration. Post-hoc event rejection and mock event tests cannot prove that gate.
- **Versions/files:** AiQQ pins `openai-codex-sdk==0.1.11` (`/home/ubuntu/AiQQ/pyproject.toml:20`; `/home/ubuntu/AiQQ/uv.lock:635`) and project-local `@openai/codex` `0.152.1` (`/home/ubuntu/AiQQ/package.json:6`); local `node_modules/.bin/codex --version` returned `codex-cli 0.152.1`. AiQQ's CLI lookup prefers that bundled binary (`/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py:103`). The unrelated global `codex` binary reports `0.156.0`, so its behavior is not the AiQQ pin.
- **SDK surface:** Installed `openai_codex_sdk/types.py:30` exposes sandbox, network, web-search, approval and cwd options, **not** a deny-all-tools option; `exec.py:51` translates these into CLI flags and `--config`. AiQQ sets read-only, network off, web search per request and approvals never (`/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py:392`); its generated config disables named feature flags including `shell_tool` and `unified_exec` (`/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py:689`). Neither is a documented comprehensive allowlist. Current official Codex SDK documentation describes the *TypeScript* `@openai/codex-sdk`, not a guarantee for the pinned Python wrapper: [Codex SDK](https://developers.openai.com/codex/sdk).
- **App-server surface:** AiQQ launches with `--disable` for a finite list of features (`/home/ubuntu/AiQQ/codex_app_server.py:668`) and sets `sandbox: read-only`, `approvalPolicy: never` and limited web/image config at `thread/start` (`/home/ubuntu/AiQQ/codex_app_server.py:492`). The app-server protocol documents per-thread sandbox/approval fields and experimental `dynamicTools` (not a built-in-tool denial switch): [Codex App Server](https://developers.openai.com/codex/app-server). The configuration reference documents individual toggles (`features.shell_tool`, `features.unified_exec`, `tools.web_search`, `tools.view_image`) but does not establish a version-locked **all-tools-off** contract: [Configuration Reference](https://developers.openai.com/codex/config-reference). Absence of a setting in current docs is not proof of every capability of the older pin.
- **Why isolation is insufficient:** OpenAI explicitly says read-only + never still permits reading files and running commands inside the sandbox: [Agent approvals & security](https://developers.openai.com/codex/agent-approvals-security). AiQQ SDK rejects unexpected `item.started` tool types only after receiving the event (`/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py:486`); its fake test injects a `command_execution` event (`/home/ubuntu/AiQQ/tests/unit/services/test_codex_sdk_backend.py:224`). AiQQ app-server similarly interrupts on a finite forbidden-item list (`/home/ubuntu/AiQQ/codex_app_server.py:38`; `/home/ubuntu/AiQQ/codex_app_server.py:860`), while other tool item types are not universally rejected. These are fail-closed *outputs*, not evidence that tools were unavailable before side effects.
- **Offline checks possible, not performed as proof:** Static option/flag inspection, version-specific app-server schema generation, clean-environment config parsing, mocked item events, and a locally stubbed upstream that records tool advertisements/returns adversarial tool calls can test particular paths without a paid endpoint. None establishes the full deployed model-turn tool catalogue or its behavior for every tool and configuration/version. Do not enable advice based on those checks alone; seek an explicit authoritative deny-all mechanism plus pre-execution negative-test evidence, or obtain the product/security decision required by the parent design.

## Related Specs

- The original strict-gate requirements were subsequently revised by the
  2026-09-24 product decision in the parent PRD/design and API child PRD.
  The current executable contract is
  `.trellis/spec/backend/codex-advice-contract.md`. The original investigation
  also consulted `.trellis/workflow.md` and the backend spec index.

## Caveats / Not Found

- No model turn, paid endpoint, or secret was loaded/called during the original investigation. This research did not execute a runtime negative test and does not claim a proof of no tools. Role-isolated `implement.jsonl` was not loaded.
