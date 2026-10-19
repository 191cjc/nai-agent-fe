# Individual Hidden Tags Deployment

## Result

Published source commit b643e47 as matched API/web release
20261019T023651 at 2026-10-19T02:37:22.851500+00:00 (10:37 China time).

Workspace: https://www.firesoul.cn/novelai/

Every shared prompt editor now supports per-tag hide/restore with muted chips.
Manual editing uses whole-line // comments; explicit blur formats safe tags
one per line. Hidden text/weights persist in history and snapshots, but never
enter the effective image prompt or experiment candidates. Search/advice/import
append across a safe line boundary. Multiline expressions and literal inline
marker contexts retain original source/manual controls. Old frozen runs retain
their original syntax and definition identity.

## Evidence

- Independent full affected-layer gate GREEN:699 offline fake backend tests
  (60 new), frozen sync/lock, Ruff, exact reviewed additive OpenAPI and web
  ESLint/TypeScript/source review. No product fixes; stale assistant append
  spec corrected. No frontend/helper/browser automated tests.
- Fresh25-input env-free locked build passed. Working/committed/build source
  sets and hashes match exactly. Staged API matches committed source and the
  pinned adjacent CLI0.152.1; deterministic side-effect-free OpenAPI and
  disposable schema4/SQLite/readiness probes pass.
- API-first publication; new optional strict prompt_comments boolean verified
  in exact running schema before web switch. No SQLite migration.
- Zero active jobs/runs before restart and after graceful shutdown. Private
  verified online backup completed first. Existing auth/session/job/run/snapshot
  rows and provider configuration preserved; no live DB restore.
- All72 retained manifest/PNG sets retain exact bytes and original expiry;
  private image ownership/modes preserved. Inventory remains root-private.
- Public HTML/JS/CSS match exact fresh-build hashes; old immutable assets and
  releases retained. Loopback/public readiness and /aiqq/health succeed.
  Unauthenticated balance returns401/no-store on loopback and public paths,
  without querying a provider. No authenticated browser assertion is implied.
- Paid/live provider/model/image/advice calls:0. No token issuance or credential
  changes. Actual interactions and resulting image appearance remain operator
  acceptance; broader editor task stays in_progress.

## Release / Recovery

API: /srv/novelai/releases/20261019T023651 (PID207197).
Web: /srv/www/novelai/releases/20261019T023651.
Previous API/web: /srv/novelai/releases/20261016T094354 and /srv/www/novelai/releases/20261016T094354.
Verified private backup: /var/backups/novelai/20261019T023651-hidden-tags/.
Root0600 activation report: /tmp/nai-hidden-tags-activation-report.json.

Keep the compatible modern API on web fallback. Old schema4 APIs ignore the
comment flag and may submit hidden source. Even pre-validation modern startup
may accept new records; use a forward fix instead of an unsafe API downgrade.
No Nginx/unit/secret configuration changes or automatic database restore.
