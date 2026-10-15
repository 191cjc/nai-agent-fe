# Reviewable Plan: Enable Production Image Provider

Status: prepared, not executed; production credential changes are outside the
retained web-only authorization and active task scope. No secret was read.
Independent review requires a matching backend refusal-boundary fix; prepare
that reviewed release and activate it before switching the corrected web.

## Exact Change

After authorization, use the existing private project `.env.local` as source
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
If checks fail after the new web is activated, restore the previous web and
environment but retain the corrected API: open tabs may still run the new
classification, so an API downgrade to the broad RuntimeError catch is unsafe.
Keep generation unavailable rather than serving that incompatible combination.
The schema/request format is unchanged; preserve backup and diagnosis records
and do not restore a database without a separate need/decision.

The restart clears transient API images and briefly interrupts API requests.
Public page/assets, readiness and `/aiqq/health` must pass afterward. These
checks and non-billable MCP discovery do not establish paid generation
success; real generation remains an explicit operator action.
