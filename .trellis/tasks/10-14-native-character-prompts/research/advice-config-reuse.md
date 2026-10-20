# Research: Reuse AiQQ AI configuration for NovelAI advice

- Query: What is the smallest safe addition needed to reuse AiQQ's existing text-AI key, HTTPS endpoint and model in this project's isolated Codex advice runtime, and where should operators edit the copied key later?
- Scope: Internal source, installed pinned SDK source and provider-free CLI help only. Parent owns all private configuration inspection, writes, restart and deployment.
- Date: 2026-10-20

## Findings

### Configuration mapping and affected files

| File | Finding |
| --- | --- |
| `/home/ubuntu/AiQQ/src/aiqq/config.py:124` | Text AI uses `OPENAI_API_KEY`, distinct from optional image-only credentials. |
| `/home/ubuntu/AiQQ/src/aiqq/config.py:125` | Text endpoint is `OPENAI_BASE_URL`, with source-code default `https://api.airoo.cc/v1`; this is a default, not proof of deployed values. |
| `/home/ubuntu/AiQQ/src/aiqq/config.py:159` | `AIConfig` keeps text key, base URL and `OPENAI_MODEL` together; model source default is `gpt-5.6-sol`. |
| `/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py:386` | AiQQ passes SDK `base_url` and `api_key` options, and thread `model`. |
| `/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py:716` | AiQQ also writes a custom `aiqq_proxy` provider with `env_key = "CODEX_API_KEY"` and Responses wire API; do not copy that credential-env construction into this project's stricter runtime. |
| `apps/api/src/novelai_api/config.py:17` | Current `Settings` has only `codex_api_key`, excluded from repr. |
| `apps/api/src/novelai_api/app.py:135` | Current default runner is created only when this key is present; it currently receives only that key. |
| `apps/api/src/novelai_api/codex_advice.py:141` | Existing runtime supplies the key to `codex login --with-api-key` by stdin, writes private per-turn auth, and suppresses auth subprocess output. |
| `apps/api/src/novelai_api/codex_advice.py:239` | Runtime environment is an explicit five-variable allowlist; host provider credentials, shell configuration and Codex home are not inherited. |
| `deploy/novelai-api.service:13` | Production settings are loaded from `/etc/novelai/api.env`. |
| `deploy/.env.api.example:1` | Operator env file is documented as root-owned mode0600; the checked-in template must contain empty secret placeholders only. |
| `apps/web/src/api.ts:263` | `503 advice_unavailable` is currently shown as `建议服务暂不可用，请重试。`; a missing key is not remedied by retries. UI wording is outside this research's implementation scope. |

Parent separately reported the deployed AiQQ configuration metadata (not read by this researcher): text backend `codex_sdk`, HTTPS base `https://api.airoo.cc/v1`, model `gpt-6.1-sol`, a present key. The existing NovelAI missing-key diagnosis is parent-provided. User authorized copying this existing configuration and requested the later editing location. Copying three selected fields into the separate NovelAI env file is preferable to importing AiQQ's whole environment or retaining a live dependency on AiQQ configuration.

### Minimal construction

Keep `NAI_CODEX_API_KEY` and add only:

```text
NAI_CODEX_BASE_URL=<optional HTTPS API root, including /v1 if required>
NAI_CODEX_MODEL=<optional model identifier>
```

Add corresponding optional `Settings.codex_base_url` / `codex_model`, and optional keyword-only runner parameters. Both absent (or exactly empty environment strings) should retain the existing default URL/model behavior. A base/model without a key must not enable advice. Do not create browser settings, a new endpoint/mode, another provider implementation or a persistent chat.

When present, pass the validated base as SDK construction option `base_url`, and the validated model as thread option `model`. Omit those keys when unset, preserving baseline tests/default behavior. Continue the existing stdin authenticator. Do **not** set SDK `api_key`, add `CODEX_API_KEY` / `OPENAI_API_KEY` to the runtime environment, inherit the AiQQ environment, read the host CLI login, or add an AiQQ custom provider requiring a credential environment variable.

Pinned installed SDK evidence:

- `apps/api/.venv/lib/python3.12/site-packages/openai_codex_sdk/types.py:23` supports optional `base_url` and `api_key`; its `env` override explicitly prevents `os.environ` inheritance (line26).
- `.../types.py:37` accepts the thread model string.
- `.../thread.py:129` forwards configured base/model into execution arguments.
- `.../exec.py:102` starts from only the supplied environment override; line112 adds `OPENAI_BASE_URL` when a base URL is configured. This value is endpoint metadata, not the API key.
- `.../exec.py:115` adds `CODEX_API_KEY` **only if** the SDK api_key option is provided; leaving it absent preserves the key-free execution environment.
- `.../exec.py:54` supplies model as a separate `--model` argument; there is no shell interpolation.
- `.../codex.py:18` constructs validated options; current `_ManagedCodex` continues using those options through its managed execution wrapper.

The existing built-in API-key login/authentication route should remain selected. A new provider block is not necessary for the minimal SDK URL override. If a future provider requires its own transport/auth semantics, treat that as a separate change; do not silently fall back to another endpoint or expose keys through request text.

### Recommended validation bounds

Use the same validation for environment-created settings and directly constructed runner options (a small shared validator avoids a weaker alternate entry path):

- Base: optional; nonempty configured value at most2048 characters; HTTPS with hostname; permit API-root path and normal explicit valid port; forbid username/password, query, fragment, backslash, whitespace and control characters. Access parsed `.port` so malformed/out-of-range ports fail validation. Reject malformed brackets/host syntax with a safe setting-name-only error. Preserve the accepted path exactly; do not silently truncate or trim source values.
- Model: optional; nonempty configured value at most128 characters; one ASCII identifier with a leading alphanumeric and only alphanumerics plus `.`, `_`, `-`, `:`, `/`. This covers the parent's selected model and common namespaced aliases while blocking whitespace/control characters. It need not be in a hardcoded provider catalog. No existence/price/compatibility claim can be made offline.
- Key: retain current private field and nonblank runner requirement. No values in exceptions, repr, logs, fixtures, output, checked-in examples or task docs. No provider credential should reach the Vite build or OpenAPI.

Numeric limits above are proposed local operator contracts, not SDK-imposed limits. Document the finally selected bounds in the advice contract and meaningful tests. Optional settings should have no effect on the public request/response schema.

### Offline checks and test scope

Current `apps/api/tests/test_advice.py` already has fake runner wiring, a fake SDK factory/authenticator, exact environment assertions, forbidden tool events, strict output validation, timeout/cancel/shutdown cleanup and fake child process cases. Extend this suite rather than testing literal prompt copies:

1. Environment parsing: absent and empty URL/model preserve `None`; representative HTTPS root with `/v1` and model are accepted; reject each dangerous URL form and invalid/overlong model without printing values. Existing setting-validation tests are currently in `apps/api/tests/test_auth.py:325`, not a separate test_config.py.
2. Default runner wiring: update fake constructor as necessary; assert configured key/base/model reach the runner; retain missing-key503 even when URL/model are configured.
3. Fake SDK turn: assert custom base reaches SDK options, model reaches thread, only explicit user text is dynamic model input, no SDK api_key option and no key in config/AGENTS/env; all isolation/capability/cleanup behavior stays unchanged. Default case should continue to omit base/model.
4. SDK execution construction, provider-free: instantiate installed SDK `CodexExec` / `CodexExecArgs` with dummy values and inspect `_build_env` / `_build_command_args` without running `exec`. Custom base adds only `OPENAI_BASE_URL`; model is one distinct `--model` value; host proxy/key/home variables stay absent.
5. Run full existing backend fake suite, frozen sync, Ruff over src/tests, offline lock check and exact unchanged OpenAPI. Keep SDK0.1.11 / CLI0.152.1 and all dependency locks pinned. No frontend/helper/browser tests or live/paid advice probes are needed.
6. Production verification can compare selected private configuration internally and report only presence/match booleans, health/readiness, API schema and private-file permissions. Check idle jobs/runs and back up before the authorized restart. Without an actual provider request, describe the result as configuration/runtime wiring verified rather than successful real AI translation.

Use a clean command environment (`env -i` with only needed PATH/HOME plus `UV_NO_ENV_FILE=1 UV_PYTHON_DOWNLOADS=never`) for backend checks. Do not source or print a production env file during automated checks.

### Operator editing location

After the one-time copy, edit the NovelAI AI key in `/etc/novelai/api.env`, variable `NAI_CODEX_API_KEY`. The optional endpoint/model fields are in that same file. A root-capable editor such as `sudoedit /etc/novelai/api.env` avoids displaying the key in the chat or command arguments. Restart `novelai-api.service` when no generation or experiment work is active to load changes. This does not update AiQQ's own key: the copied configuration is independent. A key update alone does not require rebuilding the frontend.

### Related specs

- `.trellis/spec/backend/codex-advice-contract.md`: isolated per-turn auth, key-free env, tool rejection, strict JSON,45-second deadline, two-turn concurrency, fake-only checks.
- `.trellis/spec/backend/deployment-contract.md`: private operator env, pinned adjacent CLI, idle/backup/config/image gates, forward recovery after modern API startup.
- `.trellis/spec/backend/quality-guidelines.md`: fake-only complete backend gate, Ruff and deterministic OpenAPI; no configured backend type checker.
- `.trellis/spec/backend/api-contract.md`: advice availability derives from an actual configured runner; no secret-bearing public schema.

## External References / Versions

- Installed package source: `openai-codex-sdk==0.1.11` under `apps/api/.venv/lib/python3.12/site-packages/openai_codex_sdk/`.
- Pinned project-local native CLI: `apps/api/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex`, version pin0.152.1 in `apps/api/package.json` and runtime.
- Offline CLI `login --help` confirms `--with-api-key` consumes stdin. Offline `debug models --help` advertises `--bundled` to skip refresh, but no catalog or model execution was performed.
- No external documentation was fetched by this researcher; no current-documentation claim is made.

## Caveats / Not Found

- No `.env*`, production credentials, `/proc/*/environ` or private runtime auth file was read. No production change, network/model/provider call, paid probe, token creation or git operation was performed.
- SDK construction and local CLI help establish support for the relevant inputs; they do not establish remote provider compatibility, credential validity, selected-model availability, output quality, billing or latency under the existing45-second deadline.
- Installed native binary includes `OPENAI_BASE_URL`, built-in OpenAI base URL and API-key auth strings; binary strings alone are not a behavioral auth/transport test. Native CLI Rust sources were not present in the inspected npm distribution. A real authenticated turn was deliberately not used to close that gap.
- A CLI help invocation used a nonexistent task-local CODEX_HOME and emitted only a PATH-alias warning; no host auth was accessed and no helper files were created.
- The researcher wrote only this research file. Main session must update the advice/deployment specs and task authorization notes before implementation/publication.
