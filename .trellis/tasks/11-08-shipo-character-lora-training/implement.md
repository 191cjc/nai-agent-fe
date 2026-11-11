# Execution plan

## Incremental upload amendment — 2026-11-08

- [x] Operator requested overlap between training ready characters and later dataset uploads; original three remote character snapshots are already complete.
- [x] Stop the exact all-transfer local workflow group (PID 3186640 plus rsync/SSH children); preserve all complete/partial remote data.
- [x] Implement opt-in immutable metadata bootstrap, per-job readiness/hash verification, receiver locks rejecting writes to ready data, and controller waiting only for its next unready job.
- [x] Independently verify synthetic concurrent training/upload, partial/corrupt data rejection, no overwrite after readiness, lost-response/resume and existing serial/failure/lock/backup behavior; 41 synthetic tests, targeted Ruff and compilation pass.
- [x] Bootstrap reviewed code and metadata, validate the existing first snapshots and launch Xingjiang immediately while the remaining snapshots continue uploading in the background.
- [x] Confirm actual trainer process/GPU activity plus simultaneous later-dataset transfer using metadata; leave the ordered six-character workflow running. Xingjiang has epoch-2/4 checkpoints; final later readiness occurred after both. All six active snapshots are now ready.

## Current operator amendment — 2026-11-08

- [x] Operator requested deferring style and appending Weileita, Shikong and Chaoshen after the original three characters; this directly authorizes the revised execution.
- [x] Stop the exact old local watcher, remote controller and style trainer group; retain permitted-metadata stop evidence.
- [x] Implement strict plan-pinned runtime queue metadata, deferred-stage handling, active-job backup accounting and explicit append-only snapshot extension.
- [x] Independently check synthetic regressions, targeted lint and compilation (34 synthetic tests; no unresolved findings).
- [x] Wait for the pinned Chaoshen generation run to complete; export only the new three datasets and retain original four snapshots unchanged (134/114/94 added pairs).
- [x] Archive the safely stopped style status, preserve all pending characters, configure style deferred plus six active characters, and restart one detached pipeline. Confirm local PID 3186640 alive, remote six-character queue and staging barrier present.
- [x] Complete checksum-verified restaging and verify actual Xingjiang startup through the incremental amendment above; sequential automatic continuation/backups remain active until all six finish.

## Plan gate

- [x] User approved task creation and planning.
- [x] Read project/source conventions and existing training tools without inspecting private datasets.
- [x] Pin exact ten run IDs; verify completed status, discarded/purged marks and stat-only usable counts.
- [x] Confirm GPU/base model and installed sample-shuffle source.
- [x] Write and converge PRD/design/execution plan and curate implementation/check context.
- [x] Present final training plan and obtain the required subsequent plan approval. Operator: “开始”.
- [x] Run `python3 .trellis/scripts/task.py start .trellis/tasks/11-08-shipo-character-lora-training`.

## Implementation

1. Dispatch Trellis implementation for the isolated operation scripts in `/home/ubuntu/lora-kit/aoqi_training_1108/`; main session owns task documents, remote destructive actions and training launch. Preserve other contributors' edits.
2. Implement/reuse export processing with caption overrides and schema-13 purge exclusion, pair-preserving deterministic sample mixing, a fixed four-stage plan, detached remote controller, locks, private logs and atomic status.
3. Validate against synthetic fixtures/fake trainers. Check shell/Python syntax and targeted lint where available. Confirm failures cannot advance the queue and a stale intermediate artifact cannot count as success.
4. Dispatch Trellis check on scripts and contracts; resolve material findings before remote changes.

## Operations after review

1. Refresh metadata inventory of source counts, disk capacity, remote old weights, and exact local/remote process identities. Identify historical held queues without reading their logs.
2. Stop only this remote target's old submission/controller processes and remote trainer tree; verify no queued old submission remains and GPU is idle.
3. Persist exact old-LoRA deletion manifest. Delete only enumerated old remote LoRA weights/checksum files. Verify absence, reclaimed capacity and unchanged base model. This is the irreversible boundary explicitly requested by the user.
4. Run authorized dedicated exports for all ten pinned runs into four private snapshots. Redirect raw processing output and errors to private files; report only structured counts and status. Do not open resulting images/text.
5. Transfer snapshots via the authorized SSH key to the new private operation directory; verify pairing counts and checksums without decoding. No browser/UI or public endpoint involved.
6. Launch detached sequential remote controller: style → GPT Xingjiang → GPT Nuoya → GPT Zhengli. Confirm first-stage process/model/path and queue status. Subsequent stages advance only after exit=0 and artifact validation.
7. Monitor metadata status and GPU progress, never raw logs. Distinguish SSH failures from stage failures. On failure, diagnose from static error classifications and synthetic reproduction, requesting operator inspection only if private content is required.
8. After each success, retain remote per-epoch/final checkpoints and SHA256SUMS; copy verified final weights to local `~/lora-output/aoqi_training_1108/`. Verify remote/local hashes.
9. Complete all-four validation, record exact output locations, status, counts and checksums. Update specs/journal if useful; preserve existing README/task changes, never commit without the session's authorization.

## Validation commands and evidence

- `python3 -m py_compile <new operation scripts>` and `bash -n <new shell scripts>`.
- Synthetic-only unit checks for filtering/overrides/pairing/mixing and fake subprocess stage progression/failure/locking. Test commands must not reference production DB/media roots.
- Source inspection: installed `train_network.py` DataLoader `shuffle=True`; `library/dataset.py` bucket/member shuffle and epoch reset call sites.
- SSH metadata: GPU model/utilization/memory; output filenames, sizes, counts and SHA-256; controller structured status and exit codes.
- Do not run a broad web/API suite for isolated external operation scripts unless product code changes.

## Recovery

Before destructive cleanup, scripts and plan can be revised without changing training. After old LoRA deletion there is no rollback of those requested deletions. Export/transfer preparation may be restarted in a fresh isolated directory with explicit status; uncertain training is never duplicated. A failed stage blocks later jobs until corrected. Source production database and original dataset files are never modified. Keep source training data outside result bundles and public directories.
