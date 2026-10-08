# API Implementation Plan

- [x] Scaffold Python package, dependency lock, FastAPI app and offline
  authentication tests from scratch. Provider fakes follow with integration.
- [x] Add local SQLite **file path** storage and initial migration (no database
  URL or PostgreSQL dependency); implement admin token management, cookie
  sessions, revocation, ownership and origin protection. Test migration,
  restart persistence and revocation on disposable SQLite files. Verify admin
  token issuance stores only the SHA-256 digest and requires no hashing key.
- [x] Create POSIX SQLite data files/directories privately; restrict permissive
  existing DB/WAL/SHM file modes on migration, keep existing directories
  unchanged, and make backups exclusive/private. Offline tests cover upgrades,
  symlink rejection and backup failure cleanup. Operators must secure existing
  directories and Windows ACLs; untrusted path-replacement races remain a
  deployment threat, not a solved filesystem-security guarantee.
- [x] Add generation validation, job state transitions, parameter-only history
  and deletion; serve bounded short-lived results from memory. Exercise
  multi-image, TTL, no-image-persistence and restart cases.
- [x] Add authenticated Streamable HTTP MCP adapter, non-billable deployed
  schema probe and mocked image/failure tests; never auto-retry ambiguous
  paid generation. Deployed base path works, `/mcp` returns HTML; model and
  sampler have no schema enums. Confirm supported values and actual image
  payload with operator-approved requests before production UI choices.
- [x] Add DanbooruSearch normalized `/search` adapter, explicit NSFW include,
  attribution, concurrency guard and timeout/rate-limit cases. Offline tests
  now cover the documented upstream `nsfw` string and `final_score` fields;
  response decoding is limited to 1 MiB with a 30-second overall deadline;
  valid upstream 429 `Retry-After` values are forwarded without reading its
  body or retrying, while malformed values and local busy errors omit the header;
  public REST health/search were checked during planning, but this adapter's
  normalized response has not been rechecked against the live service.
- [x] Publish deterministic `apps/api/contracts/openapi.json` and offline
  regression checks for authenticated routes, typed error statuses and
  credential-free schema generation. Model/sampler choices remain provisional;
  advice availability depends on a configured key and pinned CLI.
- [x] Reuse AiQQ's pinned Python Codex SDK/CLI pattern for a bounded,
  per-turn isolated advice runner with schema validation, cleanup and
  fail-closed tool-event tests. On 2026-09-24 the operator accepted AiQQ's
  restricted runtime instead of demanding pre-execution all-tools denial;
  record this limitation honestly (see `research/codex-tool-isolation.md`).
  The pinned CLI reports `unified_exec=true` despite a `false` setting, so the
  API must not claim complete no-tools enforcement. No custom Codex URL is
  required. Automated tests use fakes and make no paid calls.
- [ ] Run `python -m pytest -q` within the API environment and its configured
  lint/typecheck, then inspect OpenAPI for browser-visible secret leaks.
  The 119 offline tests, `uv lock --check --offline`, Python syntax and
  `npm ci --offline` pass; snapshot tests cover OpenAPI secrets and error
  shapes. Ruff could not run because its wheel is not cached; no type checker
  is configured. Actual paid advice/generation was not called by tests.

Review gates: backend contract and fake tests pass before web implementation;
no real paid provider calls during automated validation. Verify the chosen
AiQQ-equivalent restrictions and observed-tool rejection, not an impossible
claim of complete pre-execution tool denial.
