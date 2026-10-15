# Private Images and Background Experiments: Combined Quality Gate

## Result

GREEN. Both implementation owners froze source, followed by independent
trellis-check review of the complete apps/api + apps/web + database + rollout
change. The checker made no source edits. Publication is a separate step.

## Findings Resolved Before Freeze

- Image cleanup originally considered deleting unknown old directories. It
  now deletes only managed names, preserves unknown artifacts and safely
  refuses unbudgetable nested trees; offline regressions cover the boundary.
- Sorted active owners could continually reclaim all three accepted slots.
  Bounded keyset cyclic traversal rotates the starting owner; deterministic
  six-owner/three-slot regression proves later owners get opportunities.
- API combined-prompt preflight counted unchanged outer style whitespace.
  It now matches base_prompt trimming while retaining the raw 3000-character
  style bound; exact-boundary, one-over and neutral-unwrapping cases pass.
- Staging now compares full credential-free generated OpenAPI against the
  reviewed committed snapshot before any production migration or switch.

## Executed Verification

- API implementer and independent checker each ran the full sanitized frozen
  offline backend suite: **356 passed**, two existing Starlette/httpx dependency
  deprecation warnings. Independent pytest elapsed 19.47s.
- Frozen offline dependency sync with test/lint extras, Ruff over src/tests,
  uv lock --check --offline and git diff --check all passed.
- Frontend implementer and independent checker ran npm run lint (ESLint and
  tsc --noEmit): passed. No Python type checker is configured.
- Deterministic reviewed OpenAPI snapshot and schema-only construction without
  DB/image-state creation passed. Metadata never reaches provider arguments.
- Parent fresh env-free locked web build passed; all 19 current source/config/
  lock hashes equal the reviewed build manifest. See
  retention-and-background-build-verification.md for exact hashes.
- Three rollout scripts and embedded probes passed syntax/read-only review:
  /tmp/nai-image-retention-build.py, -stage.py and -activate.py. Backup/private
  modes, zero-active checks, stopped-service schema3 migration, preserved auth/
  job counts, API-first/public hashes/configuration continuity and schema-aware
  recovery were reviewed. After schema3 never restore live DB/downgrade API.

## Scope Reviewed

Private disk persistence/expiry/restart, nofollow/private modes, selected-only
reads, non-evicting image capacity/reservations/cancellation/shutdown, owner
isolation/deletion, saved metadata/huge ordinal ordering and lazy comparison;
compact exact tokenizer/decimal/grid/neutral plans; immutable settings/native
coordinates and one effective seed; transactional idempotent run creation,
claim/current/cursor/counters, active-owner uniqueness, Stop/delete guard,
worker ownership after terminal DB failure, restart reconciliation without
same-ordinal paid retry, failure continuation and fair queue admission.

Frontend single creation POST/GET-only observation, entry/login/failed logout,
uncertain create and immediate404 lock, explicit Stop only, stale session races,
ordinary-generation guards, draft/latest-history isolation, current/terminal
server snapshots, lazy saved viewer selection/image URL cleanup and arrow keys.

No frontend/helper/browser automated tests, paid generation/advice, credential,
env, unit or Nginx edits were performed. Fake regressions/static checks do not
establish real provider output or desktop/mobile interaction acceptance; the
operator will exercise those after publication. Broader task remains active.
