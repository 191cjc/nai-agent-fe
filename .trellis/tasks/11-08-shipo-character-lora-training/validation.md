# Quality gate

## Incremental training/upload gate — 2026-11-08

Independent final review passed **41 synthetic tests** (10.029 seconds), Ruff E/F/I/UP/B with Python 3.12/100-column settings, and compilation across seven source/test Python files. Type checker: not configured. No unresolved findings. Review fixed the receiver's overly broad root destination by restricting it to the selected dataset subset, and passed the dataset lock FD into its rsync child so orphan receivers cannot outlive their lock.

New tests include actual rsync behavior, first ready trainer running while later data remains absent, next trainer waiting for its own readiness, start preceding a blocked upload, complete file/hash readiness, corrupt/missing rejection, ready dataset overwrite refusal, per-subset uploads excluding immutable metadata/other ready data, and surviving receiver lock inheritance. Existing six-active/deferred-style/failure/GPU-lock/final-backup checks remain passing. Reviewers did not access SSH, production data or private logs. Actual production overlap remains a separate runtime gate below.

The production overlap gate passed: verified existing first-three datasets and launched Xingjiang at 1794141160.0378752; real epoch-2/4 checkpoints were written before the last appended dataset became ready at 1794141797.9923725. GPU utilization measured 96–100%, all six readiness markers are now present and appended upload is complete. Controller PID 5321 / trainer 5324 and local watcher PID 3197163 remain active. Evidence is in `research/incremental-overlap-timestamps.json` and `research/incremental-runtime-overlap.json`. Final completion and six verified final backups are still pending.

## Revised queue gate — 2026-11-08

Independent Trellis review of style deferral, the three appended characters and explicit snapshot extension passed with no unresolved findings: **34 synthetic tests** (8.432 seconds), Ruff E/F/I/UP/B with Python 3.12/100-column settings, and Python compilation. Type checker: not configured.

New assertions cover the actual detached startup path with style deferred, exact six-character order, no deferred artifacts or fake success, queue plan-hash/order/identity validation, uncertain active-stage refusal, six-active-job final backup completion, and append-only export of the new three datasets with every byte of the original four synthetic snapshots unchanged. Existing failure/lock/privacy regressions continue to pass. Reviewers performed no SSH or production-data operations.

Operational amendment completed so far: exact watcher/controller/style-trainer stop, zero remaining trainer-group members without SIGKILL, free controller/GPU locks, all original characters still pending, archived stopped metadata status, three final source counts 134/114/94 after Chaoshen generation completed. Remaining amended gates: private extension, explicit restaging and one detached six-character launch, six successful trainer exits/artifact validation, and six verified final local backups. Style is deferred and is excluded from the completion count.

Subsequent runtime evidence: private extension completed with 342 new pairs and unchanged original four pinned snapshots; the revised detached workflow PID 3186640 is alive. Remote metadata confirms the exact six-active/one-deferred queue and transfer barrier, with new snapshot bytes arriving. Remaining current gates are full restaging/hash verification, actual Xingjiang trainer acceptance, six successful exits/artifact validation and six final local backups. Training is not yet complete.

Scope: isolated operational source under `/home/ubuntu/lora-kit/aoqi_training_1108/`; no API/web product code was changed. Existing `apps/web/README.md` and prior task work were preserved.

Independent Trellis review passed with no unresolved findings:

- 25 synthetic-only tests across `test_pipeline.py`, `test_controller.py`, `test_ops.py`.
- Ruff E/F/I/UP/B, Python 3.12 target, 100-character lines, all seven operation Python files.
- Python compilation of source and tests.
- Type checking: not configured.

Tests cover pinned selection, owner-scoped override/discard/purge handling, pending tombstones, unchanged source DB, private diagnostics and file modes, pair-preserving deterministic mixing, all-four publication and corruption detection, nonzero/empty/intermediate/stale outputs, serial stage progression, detached inherited-FD startup, surviving trainer locks after controller SIGKILL, lost launch reply recovery, dead/zombie controller liveness, transfer sentinel and automatic final-only checksum-verified backups.

Runtime gates completed: exact old-controller/trainer stop, no residual GPU compute processes, all inventoried old LoRA deleted, unchanged base SHA-256, four real snapshots prepared with counts 479/132/136/138, style source-ID mixing verified from metadata, detached transfer workflow accepted.

Remaining runtime gates: completed transfer/checksums; first actual training acceptance; per-stage successful exits and artifacts; all-four final local backups. Visual quality remains operator acceptance.

No real training content, references, raw training logs or checkpoint metadata headers were inspected. Only source/specs and permitted metadata were used.
