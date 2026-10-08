# Proposed Commit Plan — 2026-10-08

Branch: `chore/novelai-api-quality`. The operator approved this two-commit
plan by asking to continue. The source batch is committed as `342c4cf`;
this file records the approved documentation batch as well.
All paths below were edited by this session or its assigned agents; no
unrecognized dirty paths were found. The workflow Phase 3.4 one-shot
confirmation is satisfied. No push, merge, deployment or task archive
is included in this plan.

## 1. fix(api): bound provider responses and pass quality checks

Fix MCP stream deadlines and bounded decompression, reuse the shared tag
reader, add history/resource regressions and resolve local Ruff findings.
Validation: 155 offline tests, Ruff, frozen sync/lock and unchanged OpenAPI.

- `apps/api/src/novelai_api/_http_response.py`
- `apps/api/src/novelai_api/app.py`
- `apps/api/src/novelai_api/codex_advice.py`
- `apps/api/src/novelai_api/db.py`
- `apps/api/src/novelai_api/generations.py`
- `apps/api/src/novelai_api/mcp_images.py`
- `apps/api/src/novelai_api/security.py`
- `apps/api/src/novelai_api/tags.py`
- `apps/api/tests/test_advice.py`
- `apps/api/tests/test_api_contract.py`
- `apps/api/tests/test_auth.py`
- `apps/api/tests/test_generations.py`
- `apps/api/tests/test_mcp_images.py`

## 2. docs: record API verification and refresh task guidance

Record acceptance evidence, current backend contracts and task branch,
and replace stale Git/Compose/MCP/isolation instructions while retaining
unverified production release gates.

- `.trellis/spec/backend/http-response-contract.md`
- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/provider-adapter-contract.md`
- `.trellis/spec/backend/quality-guidelines.md`
- `.trellis/tasks/09-22-novelai-image-workspace/design.md`
- `.trellis/tasks/09-22-novelai-image-workspace/handoff.md`
- `.trellis/tasks/09-22-novelai-image-workspace/implement.jsonl`
- `.trellis/tasks/09-22-novelai-image-workspace/implement.md`
- `.trellis/tasks/09-22-novelai-image-workspace/prd.md`
- `.trellis/tasks/09-22-novelai-image-workspace/research/compose-versus-k3s.md`
- `.trellis/tasks/09-22-novelai-image-workspace/task.json`
- `.trellis/tasks/09-23-novelai-api/check.jsonl`
- `.trellis/tasks/09-23-novelai-api/commit-plan.md`
- `.trellis/tasks/09-23-novelai-api/design.md`
- `.trellis/tasks/09-23-novelai-api/implement.jsonl`
- `.trellis/tasks/09-23-novelai-api/implement.md`
- `.trellis/tasks/09-23-novelai-api/prd.md`
- `.trellis/tasks/09-23-novelai-api/task.json`
- `.trellis/tasks/09-23-novelai-api/verification.md`
- `apps/api/README.md`

## Unrecognized Dirty Files

None.
