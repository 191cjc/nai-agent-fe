# Diagnosis: Repeated Unknown Submission

Date: 2026-10-15. No generation request, credential read or production
mutation was made while diagnosing.

## Evidence

- Aggregated API access records contain two generation POSTs at
  07:58:14 and 07:58:53 UTC, both HTTP 503. Only timestamps/status counts were
  emitted; no user prompts, cookies, addresses or raw logs were printed.
- Public readiness is HTTP 200/status=ok; systemd is active, PID 2754998.
  Readiness checks SQLite, not the image provider.
- Deployed app.py and generations.py hashes match the reviewed repository
  source. With the known missing executor, GenerationManager.submit raises
  before seed assignment, history creation, enqueue and any provider call.
  However, independent review found the route catches all RuntimeErrors:
  executor.submit may raise after history creation and even queue insertion.
  The existing pair alone therefore does not prove pre-acceptance refusal.
- `deployment-2026-10-14.md` records this same API PID with both providers
  unconfigured. Subsequent authorized releases changed web only. Production
  image generation therefore remains unavailable until deliberately configured.
- GenerationStore currently marks every ApiFailure status>=500 uncertain,
  masking this known pre-acceptance refusal and activating the history lock.

## Minimal Fix and Limits

First narrow the backend catch to a dedicated not-configured exception raised
only at the initial missing-executor guard; other RuntimeErrors propagate as
unknown server failures. Only after that API is active may the exact typed
pair (HTTP 503, code=provider_unavailable) from generation POST be treated as
a definite pre-acceptance refusal. Show a specific not-configured
message without submitUncertain. Retain conservative uncertainty for network
errors, invalid success responses, unknown 5xx, non-JSON proxy errors and
other status/code pairs. Do not reinterpret a terminal provider_unavailable
job error as an unsubmitted job or globally change its message.

Keep the single POST owner and every experiment halt/no-retry rule. The UI
may release its operation on a definite rejection, but never resend it by
itself. This frontend fix makes the error accurate; it does not configure the
provider or establish paid generation success.

The prepared web must not be switched against the old broad backend catch.
Use API-first order for the combined release. This is now a matched API/web
fix; the earlier web-only release plan is superseded.

The active task excludes credential changes. Preparing a separate production
configuration action is possible without reading credentials: map the existing
private NovelAI MCP endpoint/token to NAI_NOVELAI_MCP_URL and
NAI_NOVELAI_MCP_TOKEN in the operator environment, preserve other settings,
back up private state and restart the API per deployment procedure. Executing
that action needs authorization beyond retained web-only publication. No
automatic paid probe should accompany it.
