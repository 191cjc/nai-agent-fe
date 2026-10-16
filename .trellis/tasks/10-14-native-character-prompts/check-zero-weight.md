# Experiment Zero Weight — Independent Review

Date: 2026-10-16. Result: **GREEN** for the scoped implementation and static/
offline quality gate. Broader real-provider and visual operator acceptance
remains open. No production source changes were required by this review.

## Findings (fixed)

- File: `apps/api/tests/test_style_runs.py`.
  Issue: the new fake-provider regression checked submitted prompts and zero
  metadata but did not directly prove the matching saved-history round trip
  or exercise a completely omitted style through the scheduler.
  Fix: parameterized the regression for both a surviving style occurrence and
  an empty style with shared scene text; compare every saved request, effective
  seed and successful status against its exact provider call. No new provider
  or frontend test harness was introduced.
- File: `apps/api/tests/test_style_plan.py`.
  Issue: zero-omission vectors did not directly cover a Unicode prefix and a
  nested numeric token in the same removal case.
  Fix: added one golden vector retaining the Unicode siblings while omitting
  the selected complete nested token. This also checks the fixed-zero bound.

## Findings (not fixed)

No unresolved implementation or release-helper source findings. No app-source
changes, public interface changes or product decisions were needed.

## Behavior Reviewed

- Browser and Python independently parse original source offsets, select by
  occurrence index, normalize signed zero with exact integer arithmetic and
  retain all selected labels/indexes and `0.0` weights in Cartesian metadata.
  Duplicate unselected text, unsupported syntax, escaped commas/whitespace,
  brackets, numeric nesting and Unicode remain intact.
- Contiguous zero runs create nonoverlapping original-source deletions; a run
  before a survivor consumes following separators, a trailing run consumes
  preceding separators, and all removed produces `''`. Descending edit order
  preserves neighboring selected replacements even when neutral unwrapping
  or zero omission shrinks output. Ordinary prompt-editor zero semantics stay
  unchanged; nonzero numeric weights and neutral 1.0 unwrapping are preserved.
- Fixed-zero grids, including off-grid configured maxima, reduce the lazy
  conservative length bound without enumerating a product. An absent style
  reserves no comma and uses the raw shared fallback length; a surviving style
  preserves the existing outer-trim/combined bound. Reachable simultaneous
  all-zero values are checked by exact divisibility/count arithmetic before
  acceptance when shared text is blank. Browser configuration and store both
  expose the actionable Chinese preflight error before create/paid work.
- New definitions persist internal version2. Every RunStore materialization
  passes through `_state`, restoring the private version to group rendering
  after get/active/claim reconciliation/Stop/restart. Version1 retains original
  zero emphasis and validation. Same-ID canonical parameter/range comparison
  ignores only supported version1/version2 identity; other changed definition
  keys and unsupported versions conflict. Stored definitions are not rewritten,
  and interrupted ordinals are not submitted again.
- Zero metadata follows the ordinary GenerationRequest persistence path to
  owner-scoped history and the saved viewer; removed terms stay identifiable
  in comparisons. Seeds, characters/coordinates, counts, cursor/claim/Stop,
  background continuation, image retention/cache and request uncertainty paths
  are unchanged. Browser rendering remains a preview, never a paid loop.
- Schema remains3, and the existing exact OpenAPI snapshot passes unchanged.
  The private version is excluded from the public RunState/schema.

## Verification

All commands ran after the implementer froze the five production files and
two backend test files. Final test-only reviewer edits are included below.
Provider keys were unset and `UV_NO_ENV_FILE=1` was set for backend execution.

| Check | Actual result |
| --- | --- |
| `uv sync --frozen --offline --extra test --extra lint` | PASS;24 packages checked |
| `uv run --frozen --offline --extra test --extra lint python -m pytest -q` | PASS;385 tests in21.39s, fake/disposable data only |
| `uv run --frozen --offline --extra test --extra lint ruff check src tests` | PASS after final test edits |
| `uv lock --check --offline` | PASS;25 packages resolved |
| OpenAPI snapshot regression in full pytest suite | PASS;unchanged checked-in snapshot |
| `npm run lint` from `apps/web` | PASS;ESLint and `tsc --noEmit` |
| `git diff --check` | PASS |
| Python type check | Not configured;not claimed as passed |

The two warnings are dependency deprecations from FastAPI/Starlette TestClient
and anyio BlockingPortal. No frontend/helper automated tests, browser work,
paid generation/advice calls, configuration/credential changes, commits or
deployment were performed by this reviewer. The parent owns the fresh env-free
web build, source-to-release matching and production publication.

## Release Helper Source Review

Read `/tmp/nai-zero-weight-build.py`, `stage.py`, `activate.py` and the captured
baseline (the latter two use the same `/tmp/nai-zero-weight-` prefix). Did not
execute them or access production. The source enforces explicit env-free
locked inputs; working/commit/build source and dist hashes; immutable release
staging; same-schema3 private verified online backup; no-active-work checks;
API-first start/readiness/OpenAPI/configuration continuity; private image-root
preservation; public exact HTML/assets and retained old assets; neighboring
service health. Recovery keeps the validated compatible API on web fallback;
before validation an old schema3 API is considered only after proving no v2
definition exists. It never restores the live database or edits env/unit/Nginx.

Source hashes reviewed:

```text
2741e0ffd635261b4f3e68e7402478bea8aee4e6875d5232372dc2cb3ce7214f  /tmp/nai-zero-weight-build.py
33429d4969054df1cc48c177ac56c57ee248079d73c1e211602d1642ddc22383  /tmp/nai-zero-weight-stage.py
dfb86fc21c101e9c21bfd709202901bcc23cffb8dcf8db00b69ee15e6f54dc61  /tmp/nai-zero-weight-activate.py
7172dd0ef3aa058c7a52de89efb30bbfd7494e90dc71daaa5e38bbe8eb451df4  /tmp/nai-zero-weight-production-baseline.json
```

## Final Source Identity

All production hashes stayed unchanged throughout this independent review;
the parent's parallel fresh build therefore needs no repetition for these
test-only additions.

```text
1cc8f25103f5d5e38b0998d3c3e751b981e5ed11b02caca69a68b39acc9f3e50  apps/api/src/novelai_api/style_plan.py
303d7376a2e27b658dfda644aca087a910f7dc16dd929b2407afbc3fc76c0e80  apps/api/src/novelai_api/style_experiments.py
4ed1f4907b6f0b5a6af792ff6e64a53a67e56612810fd495c7f74128aefc0851  apps/api/tests/test_style_plan.py
cf69e46fbfbd68b6976576327254f8d75459a1bc0940278f0d7bff80078db220  apps/api/tests/test_style_runs.py
b4f708fccadbcf49c4b3cdde7d15e3fed7497c3c9b91302feda5d533876487d7  apps/api/contracts/openapi.json
e42d11530b3b14824287ba19849a2adcfe6a3f629bb507070b82be879e322046  apps/web/src/style-experiment.ts
bd35a826c04b945a679f9c82e0edbadbfa323709e625c9fe040e330b170326bc  apps/web/src/StyleExperiment.tsx
7b37817b1124a8c550da381c8368513ae5edf0363894b1fe70938e5ad5e91390  apps/web/src/store.ts
```
