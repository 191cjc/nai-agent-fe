# Full-height Prompt Drawer Deployment

Published source commit38c443b as web-only release20261020T082808 on
2026-10-20 at16:28 China time.

Workspace: https://www.firesoul.cn/novelai/

The expanded prompt dock now fills100% of the main canvas stage, covering
the entire image. Its body flexes into the remaining height below the toggle
and scrolls internally. All former28dvh/300px/23dvh body heights are removed.
The collapsed strip and underlying canvas size remain constant. Persistent
Generate/operation/recovery controls, header and left tools remain reachable.

## Evidence

- Independent full affected-frontend review GREEN; no product corrections.
  ESLint, TypeScript and git diff --check passed. Fresh25-input isolated
  env-free locked build passed. See check-full-height-prompt-drawer.md and
  full-height-prompt-drawer-build-verification.md.
- Exact working/committed/build source sets and hashes match. Root-owned
  release and immutable shared assets match fresh-build hashes. Public HTML,
  JavaScript and CSS match exactly; previous assets remain available.
- Public readiness and /aiqq/health return200. API release and PID603374
  unchanged before/after publication; service remains active. No API restart,
  SQLite/config/image mutation, private-image download or provider/AI request.
- No frontend/helper/browser automated tests. Actual visual interaction
  remains operator acceptance; broader task stays in_progress.

## Release / Recovery

Web: /srv/www/novelai/releases/20261020T082808.
Previous web: /srv/www/novelai/releases/20261020T073033, retained.
Unchanged API: /srv/novelai/releases/20261019T023651 (PID603374).
Deployment report: /tmp/nai-full-height-prompt-drawer-deployment-report.json.
Build source-map SHA-256:
5eb83e711d38f7426b07aa99807f8e7b799eb70420ee603c99f4a7ed68935608.

Publication verified the prior pointer/assets, atomically switched the web
pointer and retained a post-switch rollback guard. Recovery changes only the
web pointer; retain the running API and private data.
