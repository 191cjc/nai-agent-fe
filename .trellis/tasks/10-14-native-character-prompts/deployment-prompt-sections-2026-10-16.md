# Prompt Sections and Snapshot Deployment

## Result

Published source commit9f445e5 as matched API/web release20261016T064813 at
2026-10-16T06:48:40Z (14:48 China time).

Public workspace: https://www.firesoul.cn/novelai/

The editor now has shared scene/other sections and seven sections per native
person. Hidden sections keep text while excluding it from generation. Users
can save individual or selected sections into named private durable snapshots,
then import multiple snapshots in displayed order with explicit person mapping.
Import offers append (default) or replace and applies a validated draft
atomically. Legacy prompt text restores verbatim into other sections.

## Validation

- Independent full-scope review GREEN;559 credential-free offline backend
  tests passed. Frozen sync/lock, Ruff, exact additive OpenAPI and frontend
  ESLint/TypeScript passed; no configured Python type checker.
- Fresh env-free locked22-input web build passed. Committed, working and
  staged sources match; see prompt-sections-build-verification.md.
- Staged API construction/OpenAPI creates no DB/provider side effects; isolated
  schema4 migration/readiness/JSON/empty snapshot-table probes passed. Pinned
  adjacent CLI version remains codex-cli0.152.1.
- Both immediately before restart and after graceful stop: zero active jobs
  and experiment runs. No running work was interrupted.
- Private service-user online schema3 backup verified for copy hash/integrity
  and0600 ownership before migration. Schema4 migration/integrity preserved
  existing users/tokens/sessions/jobs/runs; new snapshot table initially empty.
- Running API OpenAPI exactly matches reviewed snapshot SHA-256
  `08ae8cc35927c973beb86dcd6d3982de8fb14aca053c88a471568ef68e187774`.
  API was validated before web activation.
- Existing private environment file bytes and provider-related process
  environment values unchanged. No credential values or prompt/image contents
  were printed or added to release artifacts.
- Private image root retains service ownership/mode0700. Captured manifest/PNG
  hash inventory while API stopped and verified all72 unexpired result sets/
  72 images after startup: exact manifest and PNG bytes, original expiry and
  file mode0600 preserved; zero expired during release. Detailed inventory
  stays in the root-private backup directory, outside public artifacts.
- Loopback/public snapshot GET without a session returns401,
  code unauthenticated and Cache-Control:no-store.
- Exact public HTML/JS/CSS SHA-256 match build artifacts; public API readiness
  and existing /aiqq/health return200. Previous release directories and both
  old immutable web assets remain available with unchanged hashes.
- No paid generation/advice probe, frontend/helper automated test or browser
  automation. Actual visual/keyboard/mobile interaction and provider image
  appearance remain operator acceptance. Broader task remains in_progress.

## Release and Recovery

Current API: /srv/novelai/releases/20261016T064813 (PID3446533).
Current web: /srv/www/novelai/releases/20261016T064813.
Previous API/web:20261016T060747.

Private backup: /var/backups/novelai/20261016T064813-prompt-sections/.
Activation report: root-owned0600
/tmp/nai-prompt-sections-activation-report.json.

After schema4 commits, retain the compatible new API even if the web falls
back. Older schema3 APIs reject the new DB regardless of snapshot count.
Activation recovery never restores the live database. No Nginx/unit or
credential/configuration change was needed.
