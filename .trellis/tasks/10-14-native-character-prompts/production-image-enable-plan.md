# Reviewable Plan: Enable Production Image Provider

Status: authorized, execution pending. On 2026-10-15 the operator explicitly
selected `授权接入现有配置并上线（推荐）` after preparation and review. This
supersedes the earlier web-only boundary for the exact two-key image-provider
change and matched release/restart below. No secret was read in preparation.
Independent review requires a matching backend refusal-boundary fix; prepare
that reviewed release and activate it before switching the corrected web.

## Exact Change

Use the existing private project `.env.local` as source
for only NAI_NOVELAI_MCP_URL and NAI_NOVELAI_MCP_TOKEN. Update those two entries
in `/etc/novelai/api.env`, preserving origin, SQLite path, all unrelated keys
and the existing Codex advice setting. No secret may enter a command argument,
log, commit, web build or public response. If required source values are
missing, stop for secure operator provisioning rather than inventing values.

Validate the endpoint using the application's HTTPS/no-userinfo rules and
check the MCP connection with only initialize/initialized/tools-list. No
generate, advice or other paid tool is authorized by this configuration step.
Only validation outcomes may be printed, never tokens or provider responses.

## Maintenance and Rollback

Check for active jobs without exposing prompt data. Before restarting, use
the documented private, verified database backup procedure and retain the old
operator environment under a root-only backup directory (0700, files 0600).
Write the updated environment atomically, root-owned mode 0600. Do not copy
the entire development environment, modify the service unit/Nginx, or edit
existing immutable release contents. The new release has unchanged locks,
schema and request format, with only the reviewed refusal-boundary fix.

Gracefully stop only `novelai-api`, atomically switch its pointer to the reviewed
refusal-boundary fix, then start so the new process loads the provider.
The existing migration pre-start remains unchanged; no schema change is
requested. Verify readiness, process activity and provider configuration
without printing secrets, then publish matching web assets and switch the web
pointer. Retain the previous API/web release directories and shared assets.
If startup fails before the new web is activated, restore the previous API
pointer/environment atomically while stopped and restart the previous API.
After the corrected API and its configuration have passed validation, a later
web/check failure restores the previous web while retaining the corrected
API and validated config, preserving possible active jobs. Open tabs may
still run the new classification, so an API downgrade to the broad
RuntimeError catch is unsafe. Restore the previous environment only if
configuration recovery is required and no active job would be interrupted;
keep generation unavailable rather than serving an incompatible combination.
The schema/request format is unchanged; preserve backup and diagnosis records
and do not restore a database without a separate need/decision.

The restart clears transient API images and briefly interrupts API requests.
Public page/assets, readiness and `/aiqq/health` must pass afterward. These
checks and non-billable MCP discovery do not establish paid generation
success; real generation remains an explicit operator action.

## Prepared Inputs

Work commit `be99b7d023b6c01516ebae1105f48eaf6a7aea3c` has passed the combined gate.
API `/srv/novelai/releases/20261015T082138` and web
`/srv/www/novelai/releases/20261015T082138` are installed but inactive.
See `submission-refusal-release-preparation.md` for source/artifact hashes and
checks. Revalidate active pointers, process state and staged hashes immediately
before activation; do not assume the current baseline persisted.
