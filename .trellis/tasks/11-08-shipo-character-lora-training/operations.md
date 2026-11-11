# Operation record

User approved the final plan with “开始”. The task is `in_progress`.

## Latest correction: overlap ready training and later uploads

The operator identified unnecessary GPU idle time caused by the all-snapshots remote transfer barrier. The first three character snapshots were already complete remotely, so they must not wait for the appended three uploads. The revised requirement is immutable metadata bootstrap followed by per-job verified readiness and concurrent later-dataset transfer.

Before implementation/deployment, main stopped the exact current local workflow group: PID 3186640, rsync PID 3186661 and SSH PID 3186662. All group members exited without force, with completed and partial remote files preserved. Remote metadata confirmed no accepted `status.json`/trainer, a free controller lock and no remaining rsync process for this operation. Evidence: `research/incremental-local-stop.json`, `research/incremental-remote-before.json`. Incremental implementation/review and actual first-character startup are pending until verified below; do not report training active based only on the previous upload workflow.

### Incremental deployment and actual overlap — verified

Independent final review passed **41 synthetic tests**, Ruff and compilation. Fixed receiver scope and lock inheritance during review; no unresolved findings. Reviewed source hashes are in `research/incremental-operation-source-manifest.json`; config is `research/incremental-config.json`.

Main ran metadata-only bootstrap, then dedicated remote verification published readiness for the original **132/136/138** character pairs without re-uploading their data. Started detached controller PID **5321**, then detached local transfer/watch workflow PID **3197163**. Actual Xingjiang trainer PID **5324** started at Unix time **1794141160.0378752** (2026-11-08 20:32:40 Asia/Shanghai). The uploader skipped all ready first-three datasets and continued only the unready appended datasets.

Xingjiang epoch-2 checkpoint mtime is **1794141471.196072** and epoch-4 checkpoint mtime is **1794141710.7476928**. The final appended dataset was verified ready at **1794141797.9923725** (20:43:17 Asia/Shanghai). Both real training checkpoints therefore preceded completion of the later uploads, demonstrating actual overlap. Metadata evidence: `research/incremental-overlap-timestamps.json`.

Subsequent metadata checks showed Xingjiang still training with GPU utilization **96–100%**, memory **12,946 MiB**, all six active readiness markers present and all **536,577,801** appended dataset bytes received. Local stage state is now `staged`; the remaining uploads finished during training, and the local workflow continues watching/backing up. The short final byte-sampling interval showed zero added bytes because upload had already completed; use checkpoint/readiness timestamps for overlap evidence rather than calling that sample concurrent transfer. See `research/incremental-runtime-overlap.json`.

Current queue remains **Xingjiang → Nuoya → Zhengli → Weileita → Shikong → Chaoshen**, with style deferred. The first character's epoch-4 checkpoint is progress, not final completion. Six successful final artifacts and verified local backups remain outstanding; task stays `in_progress`. Reusable contracts were captured in `.trellis/spec/backend/lora-training-contract.md`.

## Current queue amendment — 2026-11-08

The operator subsequently requested deferring style, then appended `gpt维雷塔`, `gpt时空` and `gpt超神`. The unique corresponding existing display name is `gpt维蕾塔`. Current active order: **Xingjiang → Nuoya → Zhengli → Weileita → Shikong → Chaoshen**. Style must remain deferred after these six finish.

The first upload had completed and style had started before the amendment. Main stopped exact local workflow PID 3156866, remote controller PID 3484 and trainer group 3516 after validating operation/stage and PID/start-time identity. All trainer group members exited via SIGTERM; no force was needed. Character stages were all still pending. Remote controller/GPU locks were independently acquired to confirm release; the stopped status was retained as `status.operator_deferred_style.json` (SHA-256 `93e160d34478b227daa1a2c6cba315b10fbec6ca16034fa5fac227de85aaaf12`). One early style checkpoint was retained, with no claim of style completion.

Metadata-only inventories pinned the appended runs: Weileita `b832d415-1488-4aab-879c-9f3f464bddb2` (134 usable), Shikong `748af765-72f8-41ec-91cb-b6f6571dde83` (114), Chaoshen `77cf8b27-5270-407d-b08f-ea88281246ae` (94). All have completed generation and match the original snapshot owner, with no unexpected missing retained images. Chaoshen was initially still generating; the operation waited until completion instead of exporting its partial set or rerunning the 44 failed groups.

Stop evidence, the original snapshot fingerprints, the archived-status evidence and final source inventories are under `research/queue-change-*.json` and `research/queue-addition-sources.json`. Original four dataset snapshots are to be preserved; only the three new snapshots are exported and uploaded. The amended code introduces a separate plan-hash-pinned queue with explicit style `deferred` state and six-active-job completion/backup accounting. Runtime redeployment and the new background launch remain pending in this record until verified below.

### Revised background launch — confirmed

The independent review passed 34 synthetic tests, Ruff and compilation with no unresolved findings. Dedicated `prepare.py --extend` completed: **134/114/94 added pairs**, **342 new images**, with all original four manifests unchanged and their files passing the original pinned hashes. Source snapshots now total **1,227 images**, including the deferred style's 479; the six active characters total **748 images**. Newly added image/caption bytes: **536,577,801**. No source run was regenerated.

Published matching local/remote `queue.json`: active order Xingjiang, Nuoya, Zhengli, Weileita, Shikong, Chaoshen; deferred style only; plan SHA-256 `76cb35992d885487e7e804db6d31a88cfc2d7a356bf382dacd1e2f1d0f274af9`. Prior local stage/watch/launch metadata was archived explicitly so the amended plan is restaged rather than treating the prior transfer as current.

Launched revised detached workflow PID **3186640** at Unix time **1794138601.1283262**. Verified alive and transferring **2,466 allowlisted files**. At Unix time **1794138637.6394126**, remote metadata confirmed the correct six-character queue, staging barrier present, no accepted trainer status, and **6,981,845 bytes** of newly added snapshots received. Transfer skips identical original snapshots using checksums. Training starts automatically only after full restaging/verification, then advances on successful validated artifacts and backs up six final weights. The slow upload remains in progress; do not claim that Xingjiang has started or that training is complete yet.

Latest allowed-metadata evidence: `research/queue-extension-ready.json`, `research/queue-extension-preparation-status.json`, `research/queue-config.json`, `research/queue-transfer-confirmation.json`, and `research/queue-operation-source-manifest.json`. Task remains `in_progress`.

## Old queue and LoRA cleanup — complete

- Verified and stopped the local old Nuoya controller process group by PID plus start ticks. Its plan targeted only `i-1.gpushare.com:56541` and had no held queues to resume. Historical held PIDs no longer existed.
- Sent SIGTERM to the identified remote old Nuoya trainer group; all seven processes exited without SIGKILL. GPU returned to 1 MiB used / 0% utilization with no compute processes.
- Refreshed the deletion inventory after training stopped: **131 old LoRA weights plus 21 checksum files**, 152 files total, **22,341,625,805 bytes** across 22 reviewed old output directories.
- Deleted only the exact inventoried paths, after checking size/inode/mtime identity and verifying no active trainer. Confirmed every inventoried file was absent afterwards.
- Free `/hy-tmp` space after cleanup: **38,901,731,328 bytes**. No dataset directories or source database files were changed.
- NoobAI-XL base preserved at 7,105,349,958 bytes. SHA-256 before and after cleanup:
  `6681e8e4b134c81f16533acedb0d406d7e5e366e1624b4105178c64d00b05d51`.
- Detailed permitted-metadata audit: `research/local-stop.json`, `research/remote-stop.json`, `research/cleanup-manifest.json`, `research/cleanup-result.json`.

## New pipeline — data prepared

Operation source and status directory: `/home/ubuntu/lora-kit/aoqi_training_1108/`.
Remote operation destination: `/hy-tmp/aoqi_training_1108/`.
Final-only local backup destination: `/home/ubuntu/lora-output/aoqi_training_1108/`.

Trellis implement/check agents implemented and independently checked the isolated private exporter. All four dedicated production exports completed successfully: **479 / 132 / 136 / 138 paired files**, **885 images** total. Latest discard marks matched initial expected counts; no source had an unexpected count change. Metadata summary is `research/preparation-status.json`.

Prepared dataset total size is 1,242,903,820 bytes (PNG plus caption files). The style manifest contains exactly seven selected source IDs, paired deterministic filename mixing, and maximum consecutive same-source filename streak of four. This calculation used source-ID and filename metadata only. Actual training additionally re-shuffles members and batches each epoch.

Full independent review passed: **25 synthetic tests**, targeted Ruff E/F/I/UP/B (Python 3.12 target, 100-column limit) over all seven Python files, and Python compilation. No type checker is configured. Review resolved lock inheritance into the live trainer, lost-start-response recovery, dead/zombie PID handling, concurrent staging protection and final-only backup corruption checks. No unresolved findings remain.

Reviewed source fingerprints are in `research/operation-source-manifest.json`. Implement/check agents performed no production data operations.

## Detached workflow — started

Main launched `python3 /home/ubuntu/lora-kit/aoqi_training_1108/ops.py background` successfully. Local workflow PID **3156866**, launch timestamp **1794131131.226945**. It transfers **1778 allowlisted files** (885 image/caption pairs, manifests, plan and remote controller source); raw logs and unrelated data are excluded.

The detached workflow performs checksum-verified resumable transfer, remote verification of all pairs, one remote controller submission, ordered training and per-stage final-only backups. It reconnects for transport failures and does not resubmit an accepted uncertain training stage.

Metadata-only progress: `workflow_launch.json`, `stage_status.json`, `workflow_status.json`, `remote_status.json`, `backups.json` under the local operation directory. Remote output and epoch progress are queried through `python3 /home/ubuntu/lora-kit/aoqi_training_1108/ops.py status`. Do not open private logs or data files.

At 2026-11-08 09:56:26 UTC, the detached workflow was alive and transfer metadata showed **92,152,885 / 1,242,903,820 bytes (7.4%)**, 110 completed data files. The SSH upload link is slow. A public-source-archive transfer probe confirmed the bandwidth limitation and was removed afterwards. The workflow continues independently after the assistant turn; GPU training starts only after the entire remote snapshot passes validation. Do not report the four training jobs complete while transfer is ongoing.

Installed kohya source additionally confirms every epoch calls bucket/member shuffle (`library/dataset.py:542`, `library/dataset.py:828`) and training DataLoader sets `shuffle=True` (`train_network.py:1192`). No kohya source change is needed.

## Privacy evidence

Only source/specs and permitted metadata have been inspected. No real image, thumbnail, reference, caption, dataset prompt, raw training log or safetensors metadata header has been opened or displayed. Authorized dedicated export/training processes will handle the data privately; diagnostic output is restricted to metadata and static error classes/codes.
