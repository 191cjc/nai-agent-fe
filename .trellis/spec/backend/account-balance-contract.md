# Image-service Anlas Balance

## Scope / Trigger

Applies to the account adapter/service, GET /api/account/balance, browser balance
store and workspace header. This is the configured image service's shared Anlas
account, separate from local user identity and advice API billing. No migration
or spend ledger. The current upstream generation response has no verified
actual-cost field; do not infer per-request charge/free status from estimates.

## Signatures

- GET /api/account/balance, protected by require_user, no body/query.
- Success200: {fixed: int, purchased: int, total: int, fetched_at: int}.
- Counts are strict nonnegative JavaScript-safe integers; total is the exact
  safe sum. fetched_at is server Unix seconds at successful provider fetch.
- Default provider uses existing backend-only NAI_NOVELAI_MCP_URL/TOKEN;
  create_app accepts an independent fake balance provider for tests. Application
  construction and OpenAPI generation have no provider/database side effects.

## Contracts

Only get_subscription is called after MCP initialization/tool discovery. No
paid call, estimator, get_user_data fallback or RPC retry. Prefer canonical
structuredContent; otherwise parse one JSON text block. Invalid structured
data must fail, not fall through to plausible text. Read only
trainingStepsLeft.fixedTrainingStepsLeft and purchasedTrainingSteps. Reject
bool/float/string/negative/unsafe values and unsafe sums; never coerce to zero.
No raw subscription/payment/tier/usage/identity or bearer data reaches browsers.

Account transport uses the existing bounded reader with1MiB decoded limit per
RPC and15s cooperative whole-operation deadline, HTTPX read/connect timeouts,
strict protocol/IDs, JSON/SSE and bounded gzip/deflate. No redirects. Keep paid
image transport's acceptance/no-retry/error semantics independent.

One process-level service caches successful values for5 monotonic seconds;
cached fetched_at is unchanged. Concurrent fetches, including failures, share
one in-flight operation. One HTTP caller's cancellation does not cancel the
shared fetch. No stale successful fallback, backend polling, DB operation or
generation admission slot. Shutdown cleans up owned account work.

Browser decoding validates types, bounds, safe sum and timestamp before state
acceptance. Entry/manual/visible30s refresh is independent of paid submission.
Activity uses coalesced trailing5500ms refresh beyond server cache TTL, retaining
one follow-up intent when overlapping an older in-flight query. Continuous
events cannot postpone refresh forever. Hidden tabs defer automatic polling
and refresh when visible. Preserve ordinary terminal/progress history callbacks.

Logout-start/reset/disposal clears balance, listeners/timers and aborts or
invalidates late responses. Failed logout remount reattaches without restoring
draft again. Show true zero; on refresh failure keep last known value visibly
stale with its original update time. Balance failure never blocks Generate,
sets generation uncertainty or causes a paid retry.

## Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Missing browser session |401 unauthenticated; no provider access |
| Missing configuration/tool or upstream unavailable |503 balance_unavailable |
| Upstream authentication failure |502 balance_auth_error |
| Upstream rate limit |429 balance_rate_limited |
| Cooperative deadline/network timeout |504 balance_timeout |
| Invalid tool data/protocol/encoding/decoded cap |502 balance_bad_response |
| Valid zero counts |200 with total0; UI displays0 |
| Later fetch fails |Error; old timestamp never becomes fresh |

All responses use ApiError where applicable and Cache-Control:no-store.
Messages are generic and cannot include upstream bodies, prompts or secrets.

## Good / Base / Bad Cases

- Good: a completed generation schedules a trailing read; a pre-completion
  in-flight read cannot erase that refresh intent. Last successful update time
  stays visible in accessible header details with fixed/purchased breakdown.
- Base: cached GET returns the original fetched_at; true zero renders as0.
- Bad: V5 estimator returns0, so UI promises a free request. Its upstream free
  battery can be exhausted and billing can occur. Balance movement also may
  come from another client of the configured shared account.

## Tests Required

Fake-only backend regressions verify strict values/allowlist/structured precedence,
RPC/session/auth/status/timeout/compression/size/no-retry, service TTL/concurrency/
failure/cancellation and route auth/no-store/OpenAPI without side effects.
Preserve full existing paid-generation tests. Run full frozen offline pytest,
Ruff and lock checks. Web verification uses lint/TypeScript and source lifecycle/
responsive review; no frontend/helper automated tests or browser automation.
Publish API-first with schema4-compatible backup/idle/config/image gates; any
live balance probe is read-only and must never generate an image/advice turn.

## Wrong vs Correct

- Wrong: return raw get_subscription to the browser or change cached fetched_at
  on each GET. Correct: allowlist4 normalized fields, retain provider-fetch time.
- Wrong: return0 on account error or treat balance failure as submission_unknown.
  Correct: show unknown/stale independently and leave generation state intact.
- Wrong: drop a terminal refresh because an old query is loading. Correct: keep
  one trailing intent and fetch after its completion and server cache window.
