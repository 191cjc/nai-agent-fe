# Codex Advice Runtime Contract

## Scope / Trigger

Use this contract when changing `apps/api/src/novelai_api/codex_advice.py`,
advice wiring in `app.py`, or Codex dependencies and configuration. The
operator accepted AiQQ-equivalent restricted execution on 2026-09-24, not a
proof that every tool is unavailable before execution.

## Signatures

- `POST /api/advice` accepts `AdviceRequest(input: str)` and returns
  `AdviceResult(suggestion: str)` after authentication and origin checks.
- `CodexAdviceRunner.run(text: str) -> dict` supplies one isolated SDK turn
  to `AdviceService.advise(text: str) -> AdviceResult`.
- `NAI_CODEX_API_KEY` is optional. When absent, no runner is wired and advice
  returns `503 advice_unavailable`. No custom Codex URL is required.

## Contracts

- Pin `openai-codex-sdk==0.1.11` and the project-local
  `@openai/codex==0.152.1`; verify the native CLI version before a turn.
  Install the CLI with `npm ci` in `apps/api` for runtime deployment.
- Each explicit request creates a fresh private work directory and
  `CODEX_HOME`; a per-turn `codex login --with-api-key` receives the key on
  stdin. Do not inherit a host CLI login, project files or broad process
  environment. Only the submitted advice text becomes model input; no chat
  thread is reused or persisted.
- Match AiQQ's read-only sandbox, network/search disabled, approvals `never`,
  named capability switches off, and immediate rejection of observed tool
  events. The pinned CLI still reports `unified_exec=true` despite a `false`
  setting; `shell_tool` reports disabled. This is an **accepted limitation**,
  not pre-execution tool denial. Host/process secrets must remain protected.
- Request strict JSON output with a single `suggestion` property. The public
  result is display-only. `AdviceService` caps input/output, admits at most
  two concurrent turns and sets a 45-second deadline. Abort and close the
  SDK execution before removing the temporary workspace on failure, timeout,
  cancellation and shutdown. Never write advice text or output to SQLite.

## Validation & Error Matrix

| Condition | API result |
| --- | --- |
| Missing session | `401` typed `ApiError` |
| Wrong/missing mutation origin | `403` typed `ApiError` |
| Invalid input or extra request fields | `422` typed `ApiError` |
| Missing `NAI_CODEX_API_KEY` | `503 advice_unavailable` |
| Concurrent advice capacity exhausted | `429 advice_busy` |
| Observed tool item, even after a completed turn | `502 advice_tool_attempt`; no suggestion released |
| Malformed JSON, invalid schema, SDK/CLI failure | `502 advice_failed`; no upstream details |
| Deadline exceeded | `504 advice_timeout`; abort and cleanup |

## Good / Base / Bad Cases

- Good: authenticated explicit text produces one schema-valid suggestion;
  the private turn directory disappears afterwards.
- Base: no key configured leaves the endpoint unavailable without spawning a
  CLI or reading `.env.local`.
- Bad: an observed `command_execution` or other non-message item aborts the
  turn and never returns a partial suggestion, even if seen after completion.

## Tests Required

- Use fake SDK/thread/event streams and a fake authenticator in
  `apps/api/tests/test_advice.py`; automated tests never invoke a paid model.
- Assert only submitted text reaches the SDK, key stays out of child env,
  output schema is strict, tool events fail closed, and cancellation/timeout/
  shutdown stop the child before temporary-directory cleanup.
- Verify `apps/api/contracts/openapi.json` contains no key, CLI path or
  private runtime directory, and check the package locks offline.

## Wrong vs Correct

- Wrong: treat `read-only` or `features.unified_exec=false` as proof that
  shell/filesystem tools cannot execute, or merely abort an SDK signal while
  its child keeps running.
- Correct: document the remaining capability risk, reject tool events,
  explicitly close the SDK execution, and use offline fake-event tests.
