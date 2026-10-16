# Image-service Anlas balance

## Boundary and ownership

The gap is account visibility in the existing workspace header. The backend
owns one configured MCP account. Add an isolated account adapter/service and
authenticated route, a protected browser store and header UI. Do not refactor
paid transport, add a ledger/migration, change acceptance/uncertainty/Stop, or
estimate per-request billing. Research: research/account-balance.md.

Backend owns new account modules, app.py wiring, fake backend tests and reviewed
OpenAPI. Frontend owns api.ts decoding, balance store/component, store.ts callback
composition/lifecycle, App.tsx integration and styles.css. Parent owns specs and
release artifacts. Existing section assistant behavior remains intact.

## Frozen browser contract

GET /api/account/balance, no query/body, authenticated by require_user.
200 object contains only fixed, purchased, total and fetched_at. Counts are
strict integers0..9007199254740991; total is their safe exact sum. fetched_at is
nonnegative safe integer Unix seconds at successful fetch, unchanged in cache.
Browser validates all fields/types/sum/time bounds. No raw subscription/payment,
tier/usage, account IDs or credentials. Unknown is never zero.

All responses inherit no-store. Existing ApiError shape; safe generic errors:
401 unauthenticated; 503 balance_unavailable (missing config/tool/unavailable);
502 balance_auth_error; 429 balance_rate_limited; 504 balance_timeout;
502 balance_bad_response (protocol/schema/body/tool error). No account failure
is a generation submission refusal or outcome_unknown.

## Read-only backend

Inject an independent balance provider into create_app for fakes. Default uses
existing MCP URL/token lazily: initialize, initialized notification, tools/list,
then get_subscription with{} after advertised tool/schema verification. No
generate_image, estimate_anlas_cost, get_user_data fallback or RPC retry.
Construction/OpenAPI performs no network/DB work.

Prefer structuredContent when present; otherwise one bounded JSON text content
object. Malformed structured data fails without falling back. Extract only
trainingStepsLeft.fixedTrainingStepsLeft and purchasedTrainingSteps. Reject
bool/string/float/negative/unsafe values and unsafe sums; ignore unrelated data.

Reuse bounded HTTP reader: JSON/SSE, gzip/deflate,1MiB decoded cap per RPC,
strict RPC IDs/protocol, no redirects and server-only credentials. Use15s
cooperative deadline across entire account handshake/query with HTTPX timeout
and connect bounds. Any parser reuse leaves image paid behavior unchanged.

One service per configured account caches successful balance for5 monotonic
seconds and coalesces concurrent fetches including failures. Async coordination
and off-thread synchronous transport; one caller cancellation cannot cancel
the shared fetch. No stale successful fallback, persistent client, backend
polling, DB work or generation admission slots. Clean owned tasks at shutdown.

## Protected browser observation

WorkspaceApi.balance(signal?) owns GET/decoding. Separate BalanceStore owns
balance|null, loading/error, request epoch/controller, timers and visibility.
Enter is idempotent, immediately queries; visible periodic refresh every30s,
refresh on becoming visible. Manual refresh coalesces. Keep actual fetched_at.

Compose existing GenerationStore terminal and StyleRunStore progress callbacks
in AppStore, preserving history refresh. Coalesce activity into one trailing
query after at least5500ms, beyond backend5s TTL. Later events cannot postpone
it forever. If firing during an old query, preserve one follow-up intent and
schedule after completion. Hidden pages defer automatic work until visible.
Never add a generation/advice POST.

Logout-start aborts/detaches and clears balance; failed logout remount restarts
observation without resetting drafts. resetProtected/dispose clear listeners,
timers/data and invalidate late responses. Existing API session epoch handles
401; never display a previous authenticated entry's balance.

## Header

Compact Anlas total, manual refresh and accessible details for fixed/purchased
breakdown and successful-update time. Label image-service balance, not a local
user wallet. Show true0, neutral initial loading/unavailable, keep last known
value on refresh failure with visible stale/error and original time. Do not
disrupt canvas/Generate/Stop. Narrow header keeps balance/refresh/logout usable.
No promise about actual request charges or advice billing.

## Gate and release

Meaningful fake backend regressions: strict allowlist, structured/text precedence,
protocol/auth/error/body/compression/deadline/no-retry, TTL/coalescing/failure/
cancellation, route auth/no-store and side-effect-free OpenAPI. Full frozen
offline backend suite, Ruff/lock; web lint/types/source review and fresh env-free
exact-input build. No frontend/helper tests, browser automation or paid probes.
Sync specs, commit, stage matched API-first schema4 release after private online
backup and zero-active-work gate. Preserve config/images/expiry/old assets.
Read-only authenticated balance verification is non-billable. Keep compatible
API on web fallback; record evidence and leave broader operator acceptance open.
