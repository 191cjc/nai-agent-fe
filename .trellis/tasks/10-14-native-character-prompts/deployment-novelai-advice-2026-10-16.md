# NovelAI-aware Advice Deployment

## Result

Published source commit14ff663 as matched API/web release20261016T094354
at 2026-10-16T09:44:30.516095+00:00 (17:44 China time).

Workspace: https://www.firesoul.cn/novelai/

Shared advice now explicitly targets NovelAI prompt composition and relevant
settings, preferring established English NovelAI/Danbooru-compatible tags.
Every section consultation visibly states NovelAI, its exact label and typed
scope, then only that section's existing text. All11 destinations are covered,
including distinct shared/character other. Suggestions request directly usable
comma-separated tags; consultation remains editable and explicit apply remains
unchanged. No canonical-tag verification promise is made.

## Evidence

- Independent full affected-layer review GREEN:639 clean-env fake-only offline
  backend tests, frozen sync/lock, Ruff src/tests, unchanged exact OpenAPI,
  frontend ESLint/TypeScript/source scope review and whitespace/context checks.
  No product fixes or copy-literal/frontend/helper/browser tests added.
- Three product files changed only: fixed INSTRUCTIONS, typed section seed,
  unified advice explanation/placeholder. Advice/generation/API/runtime/DB/
  dependencies and credentials unchanged; no implicit sibling/image/history
  context or automatic requests/application introduced.
- Fresh env-free locked25-input web build passed; exact working/committed/
  build source sets and hashes match. Staged API matches committed sources,
  adjacent pinned CLI remains0.152.1; exact side-effect-free OpenAPI and
  disposable schema4/SQLite/readiness probes pass.
- Zero active generation jobs/runs before restart and after graceful stop.
  Private verified online schema4 backup preceded publication. No migration
  or live DB restore; existing user/token/session/job/run/snapshot rows retained.
- Running API OpenAPI exactly matches unchanged snapshot before web switch.
  Existing environment bytes and provider process values unchanged.
- All72 retained manifest/PNG sets/images preserve exact bytes and original
  expiry. Private image root ownership/mode retained. Detailed inventory stays
  root-private, outside source/web artifacts.
- Public HTML/JS/CSS match exact build hashes; previous immutable assets and
  releases retained. Public readiness and /aiqq/health return200. Existing
  protected balance GET returns401/no-store without a session on loopback and
  public paths; this does not query the provider.
- Paid AI advice/image calls:0. No account/provider/model probe or browser
  automation. Offline/static checks establish instruction construction and
  runtime boundaries; actual suggestion quality is operator acceptance.

## Release / Recovery

Current API: /srv/novelai/releases/20261016T094354 (PID3502290).
Current web: /srv/www/novelai/releases/20261016T094354.
Previous API/web: /srv/novelai/releases/20261016T090442 and /srv/www/novelai/releases/20261016T090442.
Private verified backup: /var/backups/novelai/20261016T094354-novelai-advice/.
Root0600 activation report: /tmp/nai-novelai-advice-activation-report.json.

Retain compatible schema4 API on web fallback. Before API validation the helper
can restore the previous schema4 API without restoring SQLite/images. No Nginx,
unit or secret/config change. Broader editor task remains in_progress.
