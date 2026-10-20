# Per-section AI Translation Deployment

Published source commit 0b5c002 as matched API/web release 20261020T091846
at 2026-10-20T09:19:11.268714+00:00 (17:19 China time).

Workspace: https://www.firesoul.cn/novelai/

Each section helper now offers AI 建议 / AI 翻译 / 提示词搜索. Translation
shows current raw section text, accepts a short question and returns read-only
Chinese meanings. Requests freeze only that source/question/label/purpose;
old-source explanations are hidden after edits. Explanations cannot apply or
mutate prompts. Backend fixed instructions explicitly permit Chinese explanation
while keeping composition suggestions as English NovelAI-compatible tags.

## Evidence

- Independent full affected-layer gate GREEN: 699 existing offline fake backend
  tests, frozen sync/lock, Ruff src/tests, unchanged exact OpenAPI and web
  ESLint/TypeScript/source review. No product corrections. One activation-helper
  recovery issue was fixed and independently re-reviewed: post-start failure
  retains the API process/pointer, avoiding a second stop/start. Spec synchronized.
- Fresh isolated env-free locked 25-input production build passed. Exact
  working/committed/build file sets and hashes match. Staged API sources match
  commit, adjacent CLI reports 0.152.1, side-effect-free OpenAPI and disposable
  schema4/SQLite readiness checks pass. See check-section-translation.md and
  section-translation-build-verification.md.
- API-first publication after verified private online SQLite backup. Zero
  active jobs/runs before restart and after graceful shutdown. Schema remains4;
  existing auth/session/job/run/snapshot rows and provider configuration preserved.
  Exact running OpenAPI matches the unchanged checked-in snapshot.
- All 74 retained result sets / 74 PNGs preserve exact manifest/image bytes and
  original expiry; none expired during publication. Private image modes/owner
  verified. Inventory remains root-private; no authenticated image download.
- Public HTML/JavaScript/CSS exactly match the build hashes. Previous immutable
  assets and API/web releases retained. Loopback/public readiness and /aiqq/health
  succeed. Unauthenticated balance returns401/no-store on both routes without
  contacting a provider; no authenticated browser assertion is implied.
- No frontend/helper/browser automated tests, real AI/advice/provider/paid calls,
  credential changes or token issuance. Actual translation quality and interaction
  remain operator acceptance; broader editor task stays in_progress.

## Release / Recovery

API: /srv/novelai/releases/20261020T091846 (new PID657285).
Web: /srv/www/novelai/releases/20261020T091846.
Previous API: /srv/novelai/releases/20261019T023651 (prior PID603374).
Previous web: /srv/www/novelai/releases/20261020T082808.
Private verified backup: /var/backups/novelai/20261020T091846-section-translation/.
Root0600 activation report: /tmp/nai-section-translation-activation-report.json.

Keep the compatible modern API process and pointer on web fallback/post-start
verification failure; diagnose and forward-fix without an automatic second
restart or live database restore. No Nginx/unit/secret configuration changes.
