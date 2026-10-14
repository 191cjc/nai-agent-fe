# Commit Plan — Web Interaction Polish

All dirty files belong to work created in this session. No unrecognized dirty
files were found. Implementation and independent review are complete; see
`verification.md` for static checks and the browser-validation limitation.

## Work Batch

One coherent commit:

```text
fix(web): align tool navigation and refresh completed history
```

Include exactly these files:

- `apps/web/src/App.tsx`
- `apps/web/src/store.ts`
- `.trellis/spec/frontend/workspace-contract.md`
- `.trellis/tasks/09-23-novelai-web/task.json`
- `.trellis/tasks/10-14-web-interaction-polish/task.json`
- `.trellis/tasks/10-14-web-interaction-polish/prd.md`
- `.trellis/tasks/10-14-web-interaction-polish/research/interaction-findings.md`
- `.trellis/tasks/10-14-web-interaction-polish/implement.jsonl`
- `.trellis/tasks/10-14-web-interaction-polish/check.jsonl`
- `.trellis/tasks/10-14-web-interaction-polish/verification.md`
- `.trellis/tasks/10-14-web-interaction-polish/commit-plan.md`

The parent task metadata only links this follow-up. No other task's completion
status is changed by this batch.

## Bookkeeping After the Work Commit

After the user approves the batch, follow the normal finish-work sequence:

1. Archive only `10-14-web-interaction-polish` through `task.py archive`.
2. Record this session through `add_session.py`, referencing the work commit.

Those scripts produce the standard separate archive and journal commits.
Do not archive the parent tasks, amend, push, merge or deploy.

The user approved this exact batch and the archive/journal sequence on
2026-10-14 with "是的", satisfying workflow Phase 3.4's one-shot confirmation.
