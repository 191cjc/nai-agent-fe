# Overlay Prompt Drawer Deployment

## Result

Published source commit8217b40 as web-only release20261020T073033 on
2026-10-20 at15:30 China time.

Workspace: https://www.firesoul.cn/novelai/

The bottom prompt drawer now overlays the main canvas. A local canvas-stage
reserves the same collapsed-toggle strip in both disclosure states, so opening
the prompt body occludes the canvas without resizing or recentering its image.
The drawer height is capped to the actual stage and its content scrolls.
Generate, experiment progress/Stop, errors and uncertain-result recovery stay
outside the overlay. Mounted editor/form/disclosure behavior remains intact.

## Evidence

- Independent full affected-frontend review GREEN, no product fixes. ESLint,
  TypeScript and git diff --check passed. Fresh25-input isolated env-free
  locked build passed. See check-overlay-prompt-drawer.md and
  overlay-prompt-drawer-build-verification.md.
- Working/committed/build source sets and hashes match exactly. Root-owned
  versioned static release and shared immutable assets match build hashes.
- Public HTML/JavaScript/CSS match exact fresh-build hashes. Public readiness
  and /aiqq/health return200; previous immutable assets retain exact hashes.
- API release and PID603374 unchanged before/after publication and service
  remains active. No API restart or SQLite/config/image mutation. Previous
  web release remains available. No provider/generation/AI request or private
  image download was performed.
- No frontend/helper/browser automated tests. Narrow/short layout and focus/
  layer behavior were source-reviewed; actual visual interaction remains
  operator acceptance. Broader task stays in_progress.

## Release / Recovery

Web: /srv/www/novelai/releases/20261020T073033.
Previous web: /srv/www/novelai/releases/20261020T055052, retained.
Unchanged API: /srv/novelai/releases/20261019T023651 (PID603374).
Deployment report: /tmp/nai-overlay-prompt-drawer-deployment-report.json.
Build source-map SHA-256:
3f86e5e7dc0e8c23fbf01a3e81b746c424009fba41d6aeeb8a1b96791a489e9b.

Publication checked previous assets/pointer before atomic web switch and used
a rollback guard for post-switch checks. Recovery changes only the web pointer;
retain the compatible running API and private data.
