# NovelAI API and Provider Integration

## Goal

Deliver the authenticated FastAPI API and durable per-user parameter history for the
parent workspace. Parent requirements and AC0–AC8 remain authoritative:
`../09-22-novelai-image-workspace/prd.md`.

## Requirements

- Provide admin-issued, revocable, server-generated 256-bit random tokens,
  storing only SHA-256 digests without a token-hash key, and secure browser
  sessions; enforce owner-only parameter history and transient image results
  even after token revocation.
- Validate only the agreed text-to-image inputs; queue generation with stable
  job status, persist every submitted request's positive/negative prompts,
  settings, effective seed and outcome in local SQLite; allow deletion of an
  individual user's history record without automatic expiry. Do not persist
  generated image bytes: offer only short-lived authenticated view/download.
- Backend-only adapters for authenticated NovelAI MCP `generate_image`, public
  DanbooruSearch `/search` with NSFW candidates included, and stateless Codex
  advice with AiQQ-equivalent restricted capabilities and fail-closed observed
  tool-event rejection, no page state and no persistent advice history.
- Explicit authenticated user actions use the configured paid NovelAI/Codex
  services at runtime; automated tests inject fakes and make no paid calls.
- Typed OpenAPI models, normalized non-secret errors, health/readiness, limits,
  timeouts, cleanup, migrations and injection seams for deterministic fakes.
- Publish stable fixtures/OpenAPI contracts for the dependent web child.
- Generation history pagination returns 1-100 records per request (20 by
  default) and must not stop at 10,000 total records.

## Acceptance Criteria

- [ ] Without a valid session protected operations fail consistently; admin
  revocation immediately invalidates existing sessions and cannot disclose
  token plaintext from persistent records.
- [ ] Two different users cannot see or delete each other's prompts, jobs or
  history, or view one another's transient image results. Restart preserves
  parameter history but not image bytes; users can delete one record without
  touching another.
- [ ] Fake MCP responses and failures exercise validation, explicit seed,
  multi-image transient results, content limits, partial-failure cleanup, and stable errors
  without billable calls or leaked upstream secrets.
- [ ] Tag search returns normalized results including eligible NSFW candidates,
  honors provider concurrency/rate limits and handles unavailable/429/422.
- [ ] Advice accepts only explicit input, returns schema-valid display-only
  output, rejects any tool-call event, and cleans up after timeout/cancellation.
- [ ] Tests and generated OpenAPI document all protected paths and expected
  error/status contracts; no external service required for CI.

## Dependencies

Freeze the API contract with the parent design before the web child consumes
it. The operator accepted AiQQ-equivalent Codex isolation on 2026-09-24;
do not describe it as pre-execution all-tools denial. Deployed MCP schema
remains a separate compatibility gate.
