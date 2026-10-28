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
- Optional `NAI_CODEX_BASE_URL` and `NAI_CODEX_MODEL` configure the selected
  advice endpoint/model. Unset or empty env values retain SDK/CLI defaults.
  A configured base is an absolute HTTPS URL<=2048, with a hostname and valid
  port, no userinfo/query/fragment delimiters, backslash, whitespace or control
  characters. A configured model is nonblank<=200 without whitespace/control
  characters. Reject invalid settings without including their value in errors.
- `CodexAdviceRunner(api_key, *, base_url=None, model=None, ...)` receives the
  validated settings from `create_app`; direct construction validates them too.

## Contracts

- Pin `openai-codex-sdk==0.1.11` and the project-local
  `@openai/codex==0.152.1`; verify the native CLI version before a turn.
  Install the CLI with `npm ci` in `apps/api` for runtime deployment.
- Each explicit request creates a fresh private work directory and
  `CODEX_HOME`; a per-turn `codex login --with-api-key` receives the key on
  stdin. Do not inherit a host CLI login, project files or broad process
  environment. Alongside fixed NovelAI-oriented instructions, only submitted
  advice text becomes dynamic model input; no chat thread is reused or persisted.
- Write an explicit base as top-level `openai_base_url` (trailing `/`
  stripped) in the isolated `config.toml`, and pass an explicit model through
  `thread.model`. Omit both when absent. Never rely on SDK `options.base_url`:
  it only sets `OPENAI_BASE_URL`, which pinned CLI 0.152.1 ignores, silently
  sending turns to the default endpoint (verified 2026-10-28 with a local fake
  relay: env var → 0 requests and a 45 s hang; config key → `/v1/responses`). Keep API-key login
  on stdin; never pass SDK `api_key`, which would inject `CODEX_API_KEY`, or
  inherit a host endpoint/model/credential. Endpoint/model are backend config,
  never browser fields, prompt context or a model catalog migration.
- Fixed INSTRUCTIONS explicitly targets NovelAI image prompts and relevant
  settings. Prefer established English NovelAI/Danbooru-compatible tags,
  translating Chinese intent as needed; concise English descriptors can fill
  gaps without claiming a tag was searched or verified. Preserve requested
  intent/subject/section. Section-specific prompt suggestions contain only
  relevant comma-separated tags inside the suggestion value, without headings,
  Markdown or explanations. Keep the strict outer JSON envelope. Relevant
  generation-setting questions may still receive concise explanations.
- Explicit requests to translate/explain existing prompt meanings are an
  exception to composition's English-tag-only rule. Return concise Chinese
  meanings identifying original tags, relevant visual effects and requested
  weight/comment syntax; mark ambiguity rather than inventing canonical tags
  or claiming live verification. Do not add unrequested prompt tags. Use the
  same suggestion JSON field and keep all runtime/tool restrictions unchanged.
- Match AiQQ's read-only sandbox, network/search disabled, approvals `never`,
  named capability switches off, and immediate rejection of observed tool
  events. The pinned CLI still reports `unified_exec=true` despite a `false`
  setting; `shell_tool` reports disabled. This is an **accepted limitation**,
  not pre-execution tool denial. Host/process secrets must remain protected.
- Request strict JSON output with a single `suggestion` property. The public
  result is plain text, never executable instructions or an automatic draft
  mutation. The unified drawer displays it; the per-section frontend helper
  permits explicit user-reviewed text application under its own target/length
  contract. `AdviceService` caps input/output, admits at most
  two concurrent turns and sets a 45-second deadline. Abort and close the
  SDK execution before removing the temporary workspace on failure, timeout,
  cancellation and shutdown. Never write advice text or output to SQLite.
- A completed tool-free turn can contain intermediate `agent_message` items
  before its final answer. Match the pinned SDK's last-completed-message rule:
  validate the final message after the successful turn/stream has completed,
  without concatenating intermediate commentary or requiring a single message.
  An earlier valid JSON message cannot rescue an invalid final response.
- The pinned CLI emits non-fatal config/model warnings as `item.completed`
  items of type `error` before every turn (deprecated config key,
  under-development feature, unknown model metadata). Ignore only these
  completed warning items; `error` items in started/updated events and every
  other non-message item (command, file, MCP, web search, todo list, unknown)
  remain tool attempts. Fatal failures arrive as `turn.failed`/`error` events.
  Rejection logs record only a sanitized item type, never item text.
  Keep message/event bounds and reject tool items anywhere, including after
  turn completion; intermediate messages never bypass tool/stream validation.
- Failure logs contain only a fixed timeout/tool category or the exception's
  class name. Never log exception contents, tracebacks, submitted text, model
  output, credentials or raw upstream responses; public errors stay generic.

## Validation & Error Matrix

| Condition | API result |
| --- | --- |
| Missing session | `401` typed `ApiError` |
| Wrong/missing mutation origin | `403` typed `ApiError` |
| Invalid input or extra request fields | `422` typed `ApiError` |
| Missing `NAI_CODEX_API_KEY` | `503 advice_unavailable` |
| Concurrent advice capacity exhausted | `429 advice_busy` |
| Observed tool item, even after a completed turn | `502 advice_tool_attempt`; no suggestion released |
| Completed `error` warning items before/within a successful turn | Ignored; final suggestion returned |
| Malformed JSON, invalid schema, SDK/CLI failure | `502 advice_failed`; no upstream details |
| Intermediate commentary followed by valid final JSON and completed turn | Return the final suggestion only |
| Deadline exceeded | `504 advice_timeout`; abort and cleanup |

## Good / Base / Bad Cases

- Good: authenticated explicit text produces one schema-valid suggestion;
  the private turn directory disappears afterwards.
- Good: an upper-clothing consultation requests NovelAI-compatible shirt/sleeve
  tags for that person; its suggestion is directly usable in that section.
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
- Fake tests cover optional/default settings, invalid endpoint/model rejection,
  app-to-runner wiring and exact SDK/thread propagation. Preserve default and
  configured isolation/no-key-env assertions; no real model request is needed.
- Parser-backed fake streams cover commentary then final output, multiple final
  candidates using only the last, an invalid final after earlier valid JSON,
  and tool events after messages/completion. No real turn is needed.
- Sentinel failures assert diagnostic categories/class names are observable
  while exception contents, input and credentials stay out of logs/responses.
- Prompt/copy-only changes use the existing runtime suite and source review;
  do not add tests that merely match new literal instruction strings. No paid
  model query is required to verify prompt construction; actual suggestion
  quality remains operator acceptance.

## Wrong vs Correct

- Wrong: treat `read-only` or `features.unified_exec=false` as proof that
  shell/filesystem tools cannot execute, or merely abort an SDK signal while
  its child keeps running.
- Correct: document the remaining capability risk, reject tool events,
  explicitly close the SDK execution, and use offline fake-event tests.
