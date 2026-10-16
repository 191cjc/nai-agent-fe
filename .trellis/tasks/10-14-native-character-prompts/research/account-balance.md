# Research: Image-service balance and billing visibility

- Query: Find the smallest reliable integration for a visible remaining-credit balance and assess whether per-request paid-cost warnings can be supported.
- Scope: mixed; current repository source/specs, previously cached public upstream source, and the parent session's separately collected read-only configured-provider shape evidence. This researcher made no network/provider calls and read no credential/environment files.
- Date: 2026-10-16

## Findings

### Recommended scope

Implement the user's explicit minimum: show the configured image service's remaining **Anlas** in the workspace header, with fixed/purchased breakdown, refresh action, successful-fetch time, and clearly stale/unavailable states. Refresh independently on workspace entry and generation/experiment completion/progress. Do not change generation acceptance, unknown-outcome handling, or background-run continuation.

Do **not** implement a definitive "this request is free/paid" classification or actual-cost notification from the current evidence. V5 can silently switch from a refillable free-generation battery to Anlas billing; the verified estimator is only an estimate and does not reliably account for that state. A balance change also cannot prove the cost of one request because the configured account is shared and may be used elsewhere.

The parent independently chose this minimum after discovery. This document supplies the source evidence and edge cases for that choice; it is not authorization for paid generation or advice probes.

### Files found and code patterns

| File / anchor | Relevant existing behavior |
| --- | --- |
| `apps/api/src/novelai_api/app.py:112` | `create_app` accepts explicit fake dependencies; construction/OpenAPI must remain side-effect free. |
| `apps/api/src/novelai_api/app.py:124` | One configured server-side MCP URL/token creates the image provider; browser users do not have individual NovelAI accounts. |
| `apps/api/src/novelai_api/app.py:164` | All API responses use `Cache-Control: no-store`; mutating methods additionally check exact Origin. |
| `apps/api/src/novelai_api/app.py:176` | Protected endpoints use `Annotated[UserInfo, Depends(require_user)]`; local invalid sessions return typed 401 before provider work. |
| `apps/api/src/novelai_api/mcp_images.py:102` | Existing JSON/SSE response envelope handling rejects unrecognized/incorrect request IDs. |
| `apps/api/src/novelai_api/mcp_images.py:133` | Each generation creates an isolated MCP session and sends bearer auth only server-side. |
| `apps/api/src/novelai_api/mcp_images.py:143` | Nested RPC `send` uses bounded decoded bodies, deadlines, fixed protocol version, no redirects and safe exception mapping. It is currently generation-local, not a reusable account API. |
| `apps/api/src/novelai_api/mcp_images.py:210` | Handshake sequence: initialize, initialized notification, tools/list, exactly one paid generate_image tools/call. |
| `apps/api/src/novelai_api/mcp_images.py:239` | Generation sends width/height/steps/n_samples/model and other explicit settings. It does not currently send SMEA or billing flags. |
| `apps/api/src/novelai_api/mcp_images.py:287` | isError text mentioning Anlas/balance maps to insufficient_balance. This detects failure, not cost or payment. |
| `apps/api/src/novelai_api/mcp_images.py:301` | Only image content is consumed; other text/structured generation metadata is ignored. No verified actual-cost output exists in the current integration. |
| `apps/api/src/novelai_api/generations.py:87` | Typed request allows model/sampler strings, 1–50 steps, 64–2048 dimensions and 1–8 samples; these are app bounds, not a pricing contract. |
| `apps/api/src/novelai_api/generations.py:147` | `ImageProvider` only exposes `generate`; a balance contract should be explicit/injectable rather than assumed on every fake image provider. |
| `apps/api/src/novelai_api/generations.py:563` | Single generation worker starts only in lifespan, after DB readiness. Read-only balance refresh must not claim/consume its three admission slots. |
| `apps/api/src/novelai_api/generations.py:638` | Terminal status can be failed after paid invocation, storage failure or outcome_unknown. Refresh after both success and failure, without retrying generation. |
| `apps/api/src/novelai_api/style_experiments.py:348` | Server advances durable groups independently of browser attachment. A balance UI must observe, not stop or recreate this loop. |
| `apps/web/src/api.ts:275` | One WorkspaceApi same-origin request path, credentials included, no-store, session-version-safe 401 cleanup. Add balance here. |
| `apps/web/src/store.ts:122` | Auth epoch invalidates stale responses; logout-start and successful-end are separate hooks. |
| `apps/web/src/store.ts:515` | Ordinary generation has an epoch-checked, deduplicated first-terminal callback before image retrieval. Suitable balance-refresh trigger independent of images/history load. |
| `apps/web/src/style-run-store.ts:60` | Run accept compares processed_count/current_job_id/status and invokes onProgress only on changes after initial attachment. Current job changes can precede deduction; processed/status changes and later polling must refresh too. |
| `apps/web/src/store.ts:867` | AppStore owns API and cross-store callbacks, currently used for history refresh. Extend coordination here without components calling providers. |
| `apps/web/src/store.ts:890` | enterWorkspace deduplicates history initialization per authenticated entry; failed-logout remount reconnects experiment observation. Balance observation should similarly tolerate effect replay/remount. |
| `apps/web/src/store.ts:909` | resetProtected/dispose invalidate stores. Balance requests/timers must join those paths and logout-start invalidation. |
| `apps/web/src/App.tsx:533` | Header currently contains brand, local user label and logout. This is the requested top-of-page location. |
| `apps/web/src/styles.css:53` | Fixed 56px header and flex actions; maintain narrow-screen fit, readable balance and reachable refresh/logout. |

### Verified read-only response shape

Historical artifact `research/deployed-mcp-auto-position-schema.json:8` records these tool names: get_subscription, get_user_data, estimate_anlas_cost. It records only the generation input schema; names alone did not establish billing fields.

The parent reported fresh configured-provider read-only discovery on 2026-10-16:

```text
get_subscription input: no tool arguments
result.structuredContent: direct NovelAI subscription dictionary
result.content[0].text: JSON representing the same dictionary

subscription fields observed by shape only:
  trainingStepsLeft:
    fixedTrainingStepsLeft: integer
    purchasedTrainingSteps: integer
  tier: integer
  active: boolean
  usage:
    percent: integer
    purchasedPercent: integer
    isNegative: boolean
    timeUntilNextPercent: integer
```

No account IDs, raw values, identity data or credentials were returned to this researcher or written here. The parent owns the original discovery evidence. Prefer structuredContent; a bounded JSON text fallback may support MCP serializations that omit it. If both exist, choose one defined canonical path and reject malformed canonical data rather than silently choosing whichever produces a plausible number. No need to invoke get_user_data: it is broader and unnecessary for the required balance.

Only normalize the two observed trainingStepsLeft fields. Do not expose the whole subscription dictionary, tier, usage or identity data. usage percentages/time are not Anlas counts and must not be guessed into battery availability, remaining free requests or definitive pricing.

Suggested browser-visible successful shape (parent final design owns names):

```text
{ fixed: integer, purchased: integer, total: integer, fetched_at: integer }
total = fixedTrainingStepsLeft + purchasedTrainingSteps
```

Strict normalization should:

- Require dictionaries and exact integer values; reject Python bools, strings, floats, NaN/Infinity, missing/null fields and negative counts. Do not silently display invalid or unknown as zero.
- Bound each integer and their sum to JavaScript's safe integer range; otherwise return a safe typed bad-response error rather than round a balance.
- Preserve true zero. The UI condition must distinguish null/unavailable from total=0.
- Generate fetched_at server-side when the valid provider response was received; retain it when serving a cached value. Validate finite/safe timestamps on the browser side.
- Ignore unrelated extra upstream fields without forwarding them; upstream schema growth should not disclose private data or break the allowlist.

### Why estimate_anlas_cost cannot be a definitive warning

Previously cached public upstream source is available without credentials:

- `/tmp/aiqq-nai-v5-upstream-models.py`, SHA256 `570fb51e1ec8e8cc475a1c27dc1633e65bc7fa17b2ae9b06d26af45d0c03cd80`. This matches the model-source hash already recorded by `research/native-provider-contract.md` for public commits aa741854c1eaf4fe971498f57db8b08210bf99b3 and 49554a12938ed33856dbd8a9ce11db5f41704123.
- Its Git blob SHA `3dc226fa31d906881dcec303d8e561e38b9619a1` matches `apps/server/src/novelai_image_mcp/nai/models.py` in cached tree `/tmp/aiqq-nai-v5-upstream-tree.json`, tree SHA d568df38d42b11724b9187120ed3eb037500115f.
- `/tmp/aiqq-nai-v5-upstream-client.py:368` performs GET /user/subscription and returns the raw JSON dictionary; :375 similarly implements GET /user/data. Neither normalizes balance, free quotas or cost.

The cached model's `estimate_anlas_cost` at lines 356–391:

1. Uses max(width × height,65536), treating resolutions between 832×1216 and 1024² as 832×1216.
2. Computes ceil(ceil(2.951823174884865e-6 × resolution + 5.753298233447344e-7 × resolution × steps) × SMEA factor × strength), minimum 2 per sample.
3. SMEA factor is 1.2 for v4-family auto_smea, otherwise 1.4 for smea_dynamic or 1.2 for smea. Strength differs for img2img.
4. Defines free_sample = opus and steps<=28 and resolution<=1024², then returns per_sample × (n_samples−int(free_sample)). Multiple samples therefore do not all become free under this formula.

Its own docstring explicitly warns that V5 free generations have a refillable battery and the API can silently bill Anlas after exhaustion. Yet the implementation unconditionally subtracts one sample when opus=true and those size/step conditions hold; it does not read usage/battery state. A single-sample estimate can therefore say zero while actual billing is nonzero. Subscription tier/active alone cannot resolve this.

The parent's fresh estimator schema confirms width, height, steps, n_samples, model, action, opus and SMEA options; its description also warns about V5 silent billing. A tool description or public formula is not proof that configured-model defaults, quota state or later provider pricing match a request. The current generate_image adapter leaves SMEA defaults to the remote provider, further weakening an independently assembled estimate.

If a future feature adds pricing, label it as an estimate/range, freeze the exact effective request before confirmation, account for every sample and the full experiment product, and distinguish possible cost from observed account movement. Do not introduce a foreground-only per-group confirmation into browser-independent durable experiments. This follow-up deliberately leaves that scope out.

### Auth, privacy, caching and lifecycle considerations

- This is the **configured image service account balance**, not a local user's personal wallet or ledger. All authenticated local users reach the same configured MCP account. Label it generically as image-service Anlas and do not create owner-attributed spend history from shared-account changes.
- Keep bearer credentials on the backend. Endpoint authentication must complete before any MCP RPC; unauthenticated calls return 401/no-store without touching the provider. Keep routes under the existing /api prefix and derive the production /novelai prefix through WorkspaceApi.
- GET is appropriate for the read-only account query; inherit no-store on success and all failures. Do not append raw provider content to ApiError, logs, OpenAPI or task evidence. Missing configuration, auth failure, timeout, bad protocol and malformed subscription need safe typed errors.
- Use a dedicated short account-query timeout and small decoded response cap (e.g. 1 MiB). Reuse the bounded-body/JSON/SSE/protocol rules. Never follow remote paths/URLs or redirects. Missing get_subscription support must fail safely without invoking another tool or generation.
- Preserve the exactly-one-paid-generate call contract when sharing/extracting MCP transport code. A balance query uses one read-only get_subscription tools/call, never a generation fallback. Avoid changing paid exception classification as a side effect of a transport refactor.
- A short process-memory TTL plus single in-flight provider refresh is sufficient; no DB migration or durable balance storage is needed. Use monotonic time for TTL and wall clock only for displayed successful-fetch time. Since one provider account is configured, share cache/capacity at that provider/service level, not an unbounded cache per browser user.
- Cache responses retain the original fetched_at; manual refresh must not fabricate freshness. Do not serve stale data as a fresh successful query after an upstream error. The frontend may retain the last valid value but must visibly mark it stale/refresh-failed and show its original update time.
- Balance load failure must not overwrite draft/error/job state, block generation, mark submission uncertain, or trigger a second POST. Loading account state should not hold GenerationManager admission capacity or the paid-worker lock.
- Entry, explicit refresh and generation terminal callbacks can coalesce. If a terminal/progress invalidation happens during an in-flight pre-completion query, record one follow-up refresh intent so the older read cannot erase the need to refresh after deduction. Avoid timer storms on every two-second run poll.
- Refresh after failed as well as successful accepted jobs, including outcome_unknown. Image fetch/decode/expiry failure is unrelated and must not control balance refresh.
- During an attached experiment, use bounded periodic/progress refresh, plus refresh when final processed/status changes. A current_job_id change alone can occur before deduction. Re-entry re-fetches balance while server work continues; browser close/logout must not stop the experiment.
- Abort and epoch-invalidate requests/timers on logout start, session expiry, reset and disposal. Ignore stale successes and stale 401s from previous sessions using the existing WorkspaceApi sessionVersion. Failed logout may remount the same workspace; reconnect observation without duplicate entry effects or silently clearing a valid draft.
- If regular refresh is added, stop it when hidden/disposed and refresh on visible re-entry. Throttle repeated manual/progress events. No need for continuous background polling when no authenticated workspace exists.
- Render actual 0 as 0, initial unknown as loading/unavailable, failures as stale/unavailable. Keep balance and refresh button keyboard accessible; put verbose breakdown/update information in a bounded tooltip/popover or compact secondary text. Do not convey state by color alone or announce every background update as an alert.

### Meaningful offline verification points

Backend fake transports/services only:

- Exact get_subscription handshake/name/noargs; structuredContent and intentional bounded JSON-text fallback; arbitrary unrelated fields stripped.
- Fixed/purchased/total arithmetic, valid zero, strict bool/string/float rejection, missing/null/negative/unsafe count and unsafe sum, malformed envelopes/JSON/request IDs, isError, missing tool and incompatible protocol.
- No generation/image tool invocation for account calls, redirects disabled, decoded cap/compression/deadline, safe auth/timeout/status mapping, no raw account/token/sentinel leakage.
- Auth before remote work, 401/no-store, configured/unconfigured paths, safe errors/no-store and intentional OpenAPI snapshot update without constructor network/DB side effects.
- TTL with an injected clock, cache fetched_at stability, one in-flight refresh, successful refresh after invalidation, transient failure without false freshness, and capacity release after all errors. Do not use sleeps to prove expiry/concurrency behavior.
- Existing generation/MCP tests continue asserting exactly one paid tools/call with identical arguments and unchanged uncertain-outcome/refusal semantics; style-run continuation and no-repeat guarantees remain unchanged.

Frontend source review, ESLint/TypeScript and fresh env-free build only under the task's existing no-browser/no-frontend-automation constraint:

- Entry/effect replay, zero/unavailable/stale UI, refresh interaction, narrow header, request coalescing, completion during a pending query, terminal-before-image behavior, experiment progress/final attachment, logout during fetch, failed-logout remount and session reset.
- The balance path must remain independent of prompt/draft validation, generation busy/locks, history pagination and image cache state.

## External References

- Public cached source lineage above; no external reads were performed in this research turn.
- Pinned formula source: https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/nai/models.py#L356-L391
- Cached client maps subscription/user data to ordinary GET account routes; current deployed service version/body remains distinct from historical public source.
- Parent's separately authorized live read-only discovery verifies current tool/response shape, not successful paid generation or actual per-request billing.

## Related Specs

- `.trellis/spec/backend/api-contract.md`: safe typed responses, deterministic OpenAPI, same-origin API and pre-acceptance versus unknown-outcome boundary.
- `.trellis/spec/backend/http-response-contract.md`: decoded body cap/deadlines, bounded decompression, no automatic paid retry.
- `.trellis/spec/backend/provider-adapter-contract.md`: normalize real wire fields rather than guessing names.
- `.trellis/spec/backend/quality-guidelines.md`: explicit fakes, disposable DBs, no provider credentials or paid tests.
- `.trellis/spec/backend/durable-experiment-contract.md`: server-owned execution survives browser detach, one in-flight group and no uncertain-group retry.
- `.trellis/spec/frontend/workspace-contract.md`: protected state reset, terminal callbacks, session guards and no browser/frontend automated tests.

## Caveats / Not Found

- No verified actual per-generation charge, provider receipt or owner-attributed spend field is consumed by this app. A success or insufficient_balance failure is not a billing ledger.
- No reliable complete V5 free-battery decision model was established. Observed usage fields must not be interpreted as a count of free requests without a separate contract.
- The parent is separately clarifying whether the user also intends AI-advice API credits; this integration can show only configured image-service Anlas and must label that scope clearly.
- No code/spec/product/production changes, credential reads, git operations, frontend/browser tests or network/paid calls were performed by this researcher.
