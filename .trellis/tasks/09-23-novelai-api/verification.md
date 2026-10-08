# API Verification — 2026-10-08

Branch: `chore/novelai-api-quality`, based on `5fb7f81`.
Scope: complete `apps/api` implementation, its acceptance criteria and current
backend contracts. Source changes were committed as `342c4cf`; this report is
part of the approved documentation commit. Branch integration and production
provider readiness remain separate parent release gates.

## Results

| Check | Result |
| --- | --- |
| Full offline API suite | **155 passed**, 2 dependency deprecation warnings, 7.43 seconds |
| Ruff 0.16.8 over source and tests | **All checks passed** |
| Frozen offline test/lint dependency sync | Passed; 24 installed packages checked |
| Offline lock consistency | Passed; 25 packages resolved |
| OpenAPI exact snapshot / secret isolation | Passed; snapshot unchanged |
| API context manifests | Passed; 11 implement and 10 check entries |
| Parent context manifests | Passed; 5 implement and 3 check entries |
| `git diff --check` | Passed |
| Python type checker | Not configured |

From `apps/api`, pytest, Ruff and frozen sync ran with
`NAI_NOVELAI_MCP_TOKEN`, `NAI_CODEX_API_KEY`, `NAI_DANBOORU_SEARCH_API_KEY`,
`OPENAI_API_KEY` and `CODEX_API_KEY` removed from the child environment:

```sh
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --extra test --extra lint python -m pytest -q
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv run --frozen --extra lint ruff check src tests
env -u NAI_NOVELAI_MCP_TOKEN -u NAI_CODEX_API_KEY -u NAI_DANBOORU_SEARCH_API_KEY -u OPENAI_API_KEY -u CODEX_API_KEY uv sync --frozen --extra test --extra lint --offline
uv lock --check --offline
```

The suite uses disposable SQLite files, mock HTTP transports and fake Codex
events. It makes no live/paid calls. Ruff's exact locked wheel was downloaded
over HTTPS and verified against the SHA-256 in `uv.lock`; dependency declarations
and locks did not change. The two warnings concern Starlette's HTTPX TestClient
and the AnyIO `BlockingPortal` alias in dependencies.

## Fixed Gaps

- MCP previously buffered 64 KiB before checking deadlines on small chunks;
  fake slow streams could hold the only generation worker past the intended
  deadline. It now checks raw chunks and response-open/EOF/parse boundaries.
- HTTPX previously expanded compressed MCP responses before checking the
  decoded cap. A shared MCP/tag reader bounds zlib output allocation itself,
  validates compressed EOF and preserves provider-specific errors/no retry.
- Added **27 MCP cases** for slow chunks, decoded expansion, valid compressed
  JSON/SSE, split deflate headers, invalid compression and raw read timeouts.
- Added **9 generation cases** for history beyond 10,000 entries, pagination
  bounds, owner isolation, image/result caps, partial-result cleanup and cache
  eviction. The suite grew from 119 to 155 cases.
- Fixed 22 Ruff findings through `Annotated` FastAPI dependencies, import/UTC
  updates and line wraps, without disabling rules or changing OpenAPI.

## Child Acceptance Evidence

| PRD criterion | Evidence |
| --- | --- |
| Authentication/revocation/token secrecy | `tests/test_auth.py`, protected-route checks in `test_api_contract.py` |
| Owner isolation, restart, deletion and ephemeral images | `tests/test_generations.py`, including online backup/restore |
| MCP validation, content limits and failure cleanup | `tests/test_mcp_images.py`, generation byte-limit/partial-result regressions |
| Tag normalization, concurrency and errors | Existing `tests/test_tags.py` suite passes through the extracted reader |
| Explicit advice input, strict output and cleanup | `tests/test_advice.py`, including late tool events and cancellation |
| Browser API/schema/error contracts | `tests/test_api_contract.py`; exact OpenAPI snapshot remains unchanged |

All six API-child criteria are verified at their automated/fake boundary.
The task remains in progress pending integration; production-provider
checks remain distinct from this evidence.

## Separate Manual Integration Probe

One non-billable public `TagSearch` query for `蓝色长发` returned `long_hair`,
`blue_hair` and `blue_background` with normalized Chinese names, NSFW flags,
counts and scores, plus the expected attribution URL. It ran without a provider
key, before extracting the shared response reader. The unchanged tag regression
suite verifies the subsequent extraction. This probe is separate from automated
tests and establishes only that one public request succeeded.

## Remaining Release Gates

- Verify deployed NovelAI model/sampler values, effective seeds, actual image
  payloads and size/cost catalog; no paid generation was performed here.
- Verify real Codex authentication and a production advice turn; retain the
  accepted AiQQ-equivalent isolation limitation.
- Obtain desktop/mobile visual acceptance, configure encrypted off-host backup
  and repeat a restore drill with two accounts and pre-existing history.
- Integrate the reviewed branch, then follow task archive gates.

The shared deadline is cooperative. Individual blocked reads still rely on
HTTPX connect/read timeouts; this work does not claim an interruptible hard
wall-clock limit. No frontend/browser automation or production deployment was
performed in this follow-up.

## Production Readiness Follow-up

After the operator approved the commit plan by asking to continue, read-only
checks on 2026-10-08 established:

- Public `/novelai/`, `/novelai/api/health/ready` and `/aiqq/health` all
  returned HTTP 200. This is health evidence, not a paid-provider turn.
- The existing root-owned `/etc/novelai/api.env` has neither a configured
  NovelAI token nor a configured Codex key. The private local configuration
  has both; no values were printed, copied into production or committed.
- Using the private local NovelAI credential, non-billable MCP `initialize`,
  `notifications/initialized` and `tools/list` succeeded at the documented
  base endpoint. `generate_image` exposes all 11 adapter fields with no extra
  required fields. Model/sampler are nullable strings and dimensions are
  nullable integers; the schema does not enumerate supported model/sampler
  values or establish size/pricing tiers.
- Both local and production project-local Codex binaries pass the pinned
  `0.152.1` version check. No CLI login or model turn was performed.

The earlier MCP authentication failure is not reproduced with the current
private local credential. The production service remains provider-disabled
until its credentials are deliberately configured.

## Proposed Billable Verification

Explicit operator approval is still required before either request below.
Use the existing private local credentials in isolated application checks;
do not enable production traffic as part of these two probes.

1. One NovelAI image: positive prompt `blue_hair, long_hair`, negative
   prompt `blurry`, provisional model `nai-diffusion-4-5-full`, sampler
   `k_euler`, dimensions 512×512, 28 steps, CFG 5, seed 77, sample count 1,
   quality enabled. These IDs are candidate settings, not schema-verified
   choices. Check PNG/count and seed metadata in memory; do not archive image
   bytes or retry a failed/uncertain paid outcome.
2. One Codex advice request containing only
   `给出一句蓝色长发角色的简短提示词建议。`. Use the existing pinned isolated
   runner, 45-second deadline and strict `suggestion` JSON boundary.

These requests may incur provider charges. Actual supported values, balances
and successful outputs cannot be inferred from the successful schema/CLI probes.
