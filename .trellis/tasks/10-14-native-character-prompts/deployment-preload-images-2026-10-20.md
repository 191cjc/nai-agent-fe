# Experiment Image Preload Deployment

## Result

Published source commit c61e96c as web-only release20261020T055052 on
2026-10-20 at13:50 China time.

Workspace: https://www.firesoul.cn/novelai/

Saved experiment comparisons now offer an explicit Load All Images action with
progress and cancellation. The sequential background pass reuses cached PNGs,
continues after individual image errors and freezes its initial recorded-group
bound. Navigation and downloads remain usable. Cancellation retains completed
cache entries; capacity/errors/skipped results are explicit. Cache memory is
limited to256 images and256MiB until the comparison closes or page refreshes.

## Evidence

- Independent full affected-frontend source review GREEN; no product fixes.
  ESLint, TypeScript and git diff --check passed. Fresh25-input isolated
  env-free locked production build passed. See check-preload-images.md and
  preload-images-build-verification.md.
- Working/committed/build input file sets and hashes match exactly. New
  root-owned static release and immutable shared assets match build hashes.
- Public HTML, JavaScript and CSS match exact fresh-build hashes. Public
  readiness and /aiqq/health return200; old assets still match their hashes.
- API release and running PID207197 unchanged before and after publication;
  service remains active. No API restart, SQLite/config/image mutation,
  provider/generation request or private-result download was performed.
  Existing server experiment execution remains owned by the running API.
- No frontend/helper/browser automated tests. Interactive appearance and
  performance remain operator acceptance; broader task stays in_progress.

## Release / Recovery

Web: /srv/www/novelai/releases/20261020T055052.
Previous web: /srv/www/novelai/releases/20261019T023651, retained.
Unchanged API: /srv/novelai/releases/20261019T023651 (PID207197).
Deployment report: /tmp/nai-preload-images-deployment-report.json.
Build source-map SHA-256:
daba1226cb15e3775accd39d16d00a68c28c8adc800bf56a409c10f65d804a51.

Publication verified the previous pointer and assets before atomic web switch;
post-switch verification includes a pointer rollback guard. Recovery requires
only the previous web pointer; retain the running API and private data.
