# Integration boundaries (checked 2026-09-23)

## NovelAI Image MCP

- Project v0.4.0 source docs:
  https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/v0.4.0/apps/docs/source/tools/generate.md
- Upstream docs describe Streamable HTTP at `/mcp`, but an authorized,
  **non-billable** probe of the deployed host on 2026-09-23 found that
  `https://www.fsstudy.com.cn/novel-ai-v5` accepts `initialize` and `tools/list`
  while `/novel-ai-v5/mcp` returns HTML. Use the deployed base path in
  `NAI_NOVELAI_MCP_URL`; the operator has since corrected `.env.local`.
  The deployed server negotiated protocol `2025-06-18` with server-held
  Bearer credentials; its `generate_image` schema has the planned fields,
  but `model` and `sampler` are plain strings with no enum. The adapter
  verifies schema on each generation and never automatically retries a
  paid `tools/call`.
- `generate_image` takes `prompt`, `negative_prompt`, `model`, `width`,
  `height`, `steps`, `scale` (CFG), `sampler`, `seed` (zero means random),
  `n_samples` (1–8), and `quality` (boolean) for the chosen MVP subset.
  It returns base64 image content blocks plus text about server-side paths.
- Only image blocks are valid image payloads: never expose or attempt to use
  remote file paths. No paid result has been probed: actual model/sampler
  choices, effective seed and result payload still require verification
  before production UI choices. The deployed endpoint's exact implementation
  version is not independently verified by upstream source documentation.

## DanbooruSearch

- Provider's REST documentation and source:
  https://huggingface.co/spaces/SAkizuki/DanbooruSearch/blob/main/README.md
  https://huggingface.co/spaces/SAkizuki/DanbooruSearch/blob/main/api_fastapi.py
- Use `/api/search` with explicit `show_nsfw: true`. The provider's `TagOut`
  response model in `api_fastapi.py` declares canonical `tag`, `cn_name`,
  `nsfw` as a string, `final_score` rather than `score`, plus `category`,
  `count` and `wiki`. The provider treats `"1"` as NSFW; normalize known
  `"1"` / `"0"` values into the typed `is_nsfw` and `score` response;
  preserve unknown or absent optional fields without leaking provider
  response shape.
  Do not auto-insert a returned tag into the user's prompt.
- Provider cold starts and constrained concurrency mean the adapter needs a
  single in-flight request per deployed API instance; the chosen Compose
  topology runs one API replica. Queue briefly or return a retryable busy
  error, with separate connect/overall timeouts and HTTP 429 mapping.

## Codex advice

- Current official documentation:
  https://developers.openai.com/codex/sdk/
  https://developers.openai.com/codex/noninteractive/
  https://developers.openai.com/codex/config-basic/
- AiQQ uses the Python `openai-codex-sdk` (`Codex` and `AbortController`) with
  its pinned Codex CLI/app-server runtime. The current official Python SDK
  documentation also describes `openai-codex`/`AsyncCodex`; verify package and
  API compatibility before choosing a pinned runtime, but preserve AiQQ's
  app-server SDK integration pattern rather than substituting a bare HTTP
  chat call. A custom base URL or model override is not a product requirement.
  `codex exec` supports `--json` events and `--output-schema`. The read-only
  sandbox prevents writes, **not** the
  capability to request shell reads; default shell and subagents are enabled
  in Codex config. A dedicated clean config must disable shell, exec,
  filesystem, network search, MCP, plugins, subagents and image generation;
  an isolated scratch workspace and runtime environment must contain no
  repository, user files, credentials accessible to the model, or shared
  chat history.
- Local `/home/ubuntu/AiQQ/src/aiqq/services/ai/codex_sdk.py` demonstrates
  per-turn work/runtime isolation, cancellation, bounded concurrency and
  feature disabling. `AiQQ/pyproject.toml` pins `openai-codex-sdk==0.1.11`
  and `AiQQ/package.json` pins `@openai/codex==0.152.1`. `AiQQ` uses a custom
  model endpoint and credentials in its own environment; this workspace does
  not automatically share that configuration or require a user-supplied URL.
- Before implementing advice, pin and inspect the installed SDK/CLI version,
  confirm config/structured-output/event APIs against its own installed
  package, and test that a hostile prompt cannot invoke *any* tool. Fail
  closed if the supported runtime cannot enforce this contract; never rely
  solely on a natural-language instruction to avoid tool use. Automated tests
  must inject a fake runner and never call a paid Codex endpoint; runtime
  advice still uses the configured service when a user submits it.
