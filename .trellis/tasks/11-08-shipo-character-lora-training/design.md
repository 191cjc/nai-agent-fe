# Training design

## Current operator amendment — 2026-11-08

Latest scheduling requirement: overlap training with remaining uploads. Add opt-in plan-hash-pinned `incremental.json`; bootstrap only immutable code/plan/prepared/queue/manifests under the existing staging/controller guard. Per-job verification publishes readiness metadata only after complete file/hash checks. A per-job receiver lock rejects writes after readiness. The controller validates immutable metadata initially, waits only for the next active job's verified readiness, and validates that job before launching it. Preserve all failure, GPU-lock, serial order, deferred-style and artifact rules. The local workflow starts the detached controller before transferring remaining unready active datasets and backs up successful final artifacts. Existing complete-transfer mode remains available without incremental metadata.

Change boundary: only the isolated operation scripts/tests/README and task records. Reuse existing export, fixed snapshots and private logs. Do not change training parameters, selected runs, caption/image data, web/API behavior or create a general-purpose scheduler. Stop and verify the current local uploader process group before bootstrapping; preserve remote partial files for checksum-resumable per-job upload. There is no active character trainer at this transition.

Style training is deferred. Active order is Xingjiang → Nuoya → Zhengli → Weileita → Shikong → Chaoshen. Retain the original four snapshots unchanged; explicitly extend the fixed prepared plan with the three newly pinned runs in the PRD, exporting only the new datasets after their generation completes. Runtime queue metadata pins the plan hash and records style as deferred, never as succeeded. Completion/backup accounting includes only the six active characters. Existing uncertainty and process-identity rules still apply. Main owns stop/migration/deployment; the implement agent owns isolated operation code and synthetic verification.

The prior controller had started style shortly before this amendment. Stop its exact controller/trainer identities and the local watcher before changing the schedule; archive metadata status, verify the complete trainer process group exited, then migrate only that operator-cancelled style state to deferred. All character stages must remain pending; do not reset any uncertain character stage or reuse style outputs.

## Boundaries

This is one operational training pipeline with a single GPU lock, fixed dataset selection, destructive cleanup followed by four ordered stages, and one shared acceptance gate. Keep it as one task because the controller, cleanup identity, data snapshots, and cross-stage ordering are the direct deliverable. Do not change API/web functionality or unrelated existing work.

The local host coordinates data export/staging and final checkpoint backup. The GPU host runs a detached sequential controller under a new private directory, `/hy-tmp/aoqi_training_1108/`. Implementation code and local status live under `/home/ubuntu/lora-kit/aoqi_training_1108/`. Task records contain only permitted metadata.

AI access is limited to source code, built-in libraries/specs, dataset names/IDs, status, counts, sizes, file names, timestamps and checksums. Dedicated export/training processes consume the authorized datasets with all raw stdout/stderr redirected to private files. Never print raw training logs, exception values, captions, prompt text, image bytes, thumbnails, references, or safetensors metadata headers. The operator's instruction permits using the data for this training; it does not authorize AI inspection.

## Fixed jobs

| Order | Job | Trigger | Images now | Repeats | Expected steps before bucket rounding |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | style_shipo_1108 | aoqishipo | 479 | 1 | about 1440 |
| 2 | char_xingjiang_gpt_1108 | aoqixingjiang | 132 | 3 | about 1188 |
| 3 | char_nuoya_gpt_1108 | aoqinuoya | 136 | 3 | about 1224 |
| 4 | char_zhengli_gpt_1108 | aoqizhengli | 138 | 3 | about 1248 |

All jobs start independently from `/hy-tmp/models/NoobAI-XL-v1.1.safetensors`, never the prior stage's weights. Baseline: 1024 resolution with buckets 512..2048, no upscale, batch 4, 12 epochs, checkpoint every 2 epochs, UNet-only LoRA rank 32 / alpha 16, AdamW lr 1e-4, cosine decay / warmup 70, min-SNR 5, bf16 training / fp16 checkpoint. Use the existing NoobAI quality prefix and preserve the first trigger token when caption tokens shuffle. Do not combine text-encoder-output caching with caption shuffling.

Final image counts come from the export snapshot, since the operator can change discard marks before export. A changed count is recorded and validated, not silently replaced with another run. Missing unexpected files or zero usable sets stop preparation for diagnosis. Do not re-generate failed source groups.

## Data path and mixing

Use the established export logic in `~/lora-kit/nuoya_gpt_aoqi_1107/build_dataset.py` as the starting point; isolate any changes in the new operation directory. Preserve current caption overrides and reference/style caption behavior. Add explicit schema-13 purge exclusion (including pending tombstones) and owner/job-scoped mark handling. Only the export program handles private content. Validate with synthetic database/image fixtures and mock transfers.

Export all four datasets up front, so the seven-day source retention window cannot remove a later role during queue execution. Export the seven style runs into one repeat-1 training subset with one trigger. Shuffle the image/caption filename pairs using a deterministic seed before training; persist only index/source-ID metadata if needed. Never inspect file contents to establish pairing. Do not rebalance small face/background sets or introduce extra repetitions by source: preserve selected-image proportions.

The installed kohya training code additionally shuffles bucket members and batch indices each epoch. `--shuffle_caption` is a separate token-order feature and is not evidence of sample mixing. Check installed source and a synthetic pairing/mixing fixture; no real-image previews or training sample generation.

## Cleanup and process ownership

Before mutation, snapshot the exact local controller/queue process identities (PID plus start ticks, executable/script and target host/port) and the remote trainer session/process tree. Current old controller is `~/lora-kit/nuoya_gpt_aoqi_1107/run_job.py`, running a previous Nuoya job. Inspect known historical held queues by identity so they cannot resume and resubmit old work. Another host's queue is out of scope.

Stop only the identified old controller and its submission/wait descendants, and the identified remote old trainer session. Recheck PID identity before signals; ensure the old controller cannot resume held work in its `finally` path. Verify GPU training is idle and no old scheduler can submit again before deleting outputs. Do not indiscriminately kill all Python processes.

Refresh the old artifact inventory after stopping training. Enumerate old `*.safetensors` in reviewed old `/hy-tmp/<job>/output/` directories plus stale checksum files; remove only these old LoRA artifacts. Exclude `/hy-tmp/models/`, the new operation directory, source datasets, environment, caches, and unrelated paths. Initial inventory: 128 weights / 21,829,977,392 bytes across 22 output directories; the count can grow while old training is running. Record exact before/after paths, sizes and deletion results without opening checkpoint headers. Verify the base model remains the same size/checksum.

Deletion is irreversible and was explicitly requested by the operator. Do not make a new unwanted backup of old LoRA artifacts. Preserve prior local downloaded results because the request's deletion scope is the named remote server.

## Durable execution and outputs

Use atomic metadata-only status updates and an exclusive operation lock. Transfer/stage may retry interrupted transfers with checksums; training does not automatically rerun an uncertain accepted job. All datasets must be staged and file-pair counts verified before starting the remote controller.

The remote controller launches one training subprocess at a time and waits for its actual exit code. A nonzero code or missing/empty final checkpoint marks the stage failed and prevents later stages from starting. A lost SSH session does not imply training completion and must not launch duplicate work. On success, generate SHA-256 for all stage checkpoints and update status before advancing. Do not use global `pgrep` disappearance or an intermediate checkpoint as success evidence.

Keep per-epoch and final weights remotely under the new operation directory. Download each verified final checkpoint plus checksums to `~/lora-output/aoqi_training_1108/`; no training images/captions are included in downloadable result packages. Backups must match remote checksums. Do not automatically shut down/release the rented instance.

## Verification and limits

Check synthetic export selection/override behavior, purge/discard filtering, filename pairing, deterministic mixing, serial stage order, stop-on-failure, idempotent controller locking and checkpoint success conditions. Source review must also verify private logs never reach the assistant or public web.

Runtime verification uses only status, processes, GPU utilization, exit codes, counts and hashes. Report launch separately from all-four completion. Estimated duration is deferred until actual progress metadata exists; visual quality is an operator acceptance step.
