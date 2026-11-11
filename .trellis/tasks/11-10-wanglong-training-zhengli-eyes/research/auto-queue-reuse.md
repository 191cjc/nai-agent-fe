# Research: fixed three-run timer automation reuse

- Query: Find the smallest robust reusable root systemd timer dispatcher for the three current GPT runs, using existing frozen training sources, with independent upload, serialized training, and no local model backup.
- Scope: internal; source and existing task/spec documents only.
- Date: 2026-11-10

## Findings

### Fixed scope and identity

Only these source runs are authorized, all owned by `48fd7397-53cc-422a-8bac-69293871848c`:

| Role | Source run | Trigger |
| --- | --- | --- |
| 死令 | `11fde849-209e-4fd0-85d1-15f14a2c875a` | `aoqisiling` |
| 正理 | `16dd3f0f-1a8a-4a03-abe6-569f462051d6` | `aoqizhengli` |
| 博加丘 | `916a6dd9-74fe-4e69-b876-a7a1725ea275` | `aoqibojiaqiu` |

Use three independent new roots. Each pins completed Huangjin as its fixed prerequisite, solely as an execution guard: the training base remains independent NoobAI-XL v1.1. The supplied Huangjin plan hash is `8320c7e3d74fc560d43a5b969405eebc9a87faea8836491f366eb06de5cf13a9`; its operation/root are `aoqi_training_1110_huangjin` and `/hy-tmp/aoqi_training_1110_huangjin`. This report did not independently query remote completion.

### Files found

- `/home/ubuntu/lora-kit/aoqi_training_1110_huangjin/common.py`: fixed one-job identity, immutable plan, dataset/manifest validation, atomic metadata writes and inherited-file-description locks.
- `/home/ubuntu/lora-kit/aoqi_training_1110_huangjin/prepare.py`: private completed-run exporter, owner scoping, caption overrides, discard/purge exclusion, atomic snapshot publication.
- `/home/ubuntu/lora-kit/aoqi_training_1110_huangjin/ops.py`: private SSH/rsync wrapper, complete staging, incremental bootstrap/upload, status and model backup paths.
- `/home/ubuntu/lora-kit/aoqi_training_1110_huangjin/remote_train.py`: reviewed baseline trainer, detached controller, status and artifact checksums; launcher lacks GPU-lock-before-acceptance.
- `/home/ubuntu/lora-kit/aoqi_training_1109_moyan2/remote_train.py`: fixed predecessor checks and correct atomic inherited GPU-lock launch.
- `/home/ubuntu/lora-kit/aoqi_training_1109_moyan2/test_predecessor.py`: synthetic prerequisite identity/hash/failure/lock tests.
- `/home/ubuntu/lora-kit/aoqi_training_1109_moyan2/test_controller.py`: synthetic detached/orphan lock inheritance, uncertain-stage refusal and artifact verification tests.
- `/home/ubuntu/lora-kit/aoqi_training_1109_moyan2/test_ops.py`: upload-before-wait, lost-launch-reply reattachment and blocked-predecessor tests.
- `.trellis/spec/backend/lora-training-contract.md`: privacy, immutable acceptance, readiness, shared GPU exclusion, fixed predecessor and fail-stop contracts.

### Existing functions to reuse

1. Preserve the Huangjin exporter unchanged. `prepare.py:90` (`resolve_owner`) requires the exact owner/run in `completed` state. `prepare.py:107` (`source_rows`) selects successful jobs with owner-scoped overrides and all discard/purge intents. `prepare.py:133` (`export_job`) consumes private data inside the dedicated program, checks nonempty source files, writes paired outputs and hashes, and rejects zero retained images. `prepare.py:211` (`prepare`) takes `.prepare.lock`, opens a read-only SQLite snapshot transaction, publishes plan/manifests atomically, and reuses an already prepared snapshot after verification.
2. Reuse Huangjin `common.py:93` (`verified_manifest`), `:118` (`verified_dataset`), and `:140` (`verify_prepared`). They bind source runs, exact file sets, sizes and hashes, and reject changed plans/manifests.
3. Reuse Huangjin `ops.py:64` (`private_command`), `:99` (`remote`), `:122` (`transfer_files`), `:143` (`bootstrap`), `:178` (`readiness`), and `:189` (`upload_pending`) with the backup call removed in the new source. Metadata bootstrap and dataset readiness allow each completed source to transfer immediately, irrespective of the other two sources or GPU use.
4. Port Moyan2 `remote_train.py:62` (`predecessor_status`) and `:129` (`require_predecessor`) with the fixed Huangjin identity. It verifies plan/prepared/status identity, every succeeded stage's actual exit 0, and actual artifact sizes/hashes. `:308` (`verify_success`) verifies all recorded model artifacts without opening headers.
5. Port Moyan2 `remote_train.py:370` (`controller`), `:542` (`launch`), and CLI `--gpu-lock-fd` plumbing. The launcher acquires both operation and GPU locks before writing `launching`; it passes both descriptors into the detached controller, which retains them and passes them to the trainer. Predecessor is rechecked before acceptance, inside the inherited-lock controller, and before trainer creation. Preserve Huangjin's training-command baseline and pair-mixing seed.
6. Reuse `common.exclusive_lock` close-only behavior (Huangjin `common.py:69`), `atomic_json` (`:43`), and PID/start-tick identity (`remote_train.process_start_ticks`). Closing rather than explicit unlock permits orphan children to retain exclusion.

### Important reuse hazards

- Huangjin `remote_train.py:447` acquires only `.controller.lock` before acceptance. Its child acquires the GPU lock later. Three schedulable operations must use the Moyan2 atomic launcher, otherwise two operations can become accepted before discovering GPU contention.
- Moyan2 `gpu_lock_path` (`remote_train.py:56`) derives the lock filename from the predecessor operation. Changing the predecessor to Huangjin without changing this helper selects the wrong lock. Fix the absolute path to **`/hy-tmp/.aoqi_training_1109_v3.gpu.lock`**, shared with existing operations.
- Huangjin `ops.py:209` calls `backup(args)` unconditionally after incremental upload. `ops.watch` and `workflow/background` also download finals. The operator prohibited all local model backup. Remove the reachable backup operations in the **new, unaccepted source only**; do not modify frozen Wanglong/Huangjin or invoke their upload/watch/workflow/background commands.
- Existing `status_summary` reports structured state but does not recompute completed model hashes. Before advancing after a completed accepted task, call an explicit metadata-only completion-verification action wrapping `verify_success`, and check every stage exit 0 plus nonempty final and epoch artifacts.
- Moyan2 predecessor constants are currently outside `fixed_plan()`. In new operations, add the fixed predecessor root/operation/plan hash/ordered jobs/triggers/final names and absolute GPU lock to the immutable plan, so `prepared.plan_sha256` binds the intended execution guard. Verify config equality; do not allow timer arguments or a mutable external file to change accepted gate identity.
- Importing three operation directories into one long-lived Python process under names `common`/`ops` causes module-cache collisions. Use a separate Python subprocess for each fixed root; source files may be cloned from one pinned template.

### Minimal dispatcher design

Create one fixed scheduler directory containing one dispatcher, one three-entry metadata config, pinned source-only templates, and metadata-only status. Keep application code unchanged.

1. Root systemd runs a singleton `Type=oneshot` tick with `UMask=0077`, explicit application-venv Python and working directory. Timer uses `OnBootSec=30s` and `OnUnitInactiveSec=30s` so a slow upload cannot create overlapping ticks. A local `.dispatch.lock` also guards manual runs. Do not detach a second infinite background loop.
2. Each tick queries only owner/run status and successful-job aggregate counts for the three fixed run IDs. A running source is `waiting_generation`; a terminal failed source is blocked, never regenerated. On `completed`, freeze its successful-image aggregate `sum(image_count)` into a newly generated one-job source/plan. The private exporter independently honors discard/purge marks and records its true retained count. The old exporter treats `expected` as comparison metadata (`prepare.py:166`), so retained count need not equal that aggregate after marks. Never rewrite a generated or accepted root to adjust counts.
3. For every source that is completed and not yet snapshotted, invoke the dedicated exporter with the fixed owner and root, keeping stdout/stderr private except its structured counts/status. Prepare only this source; do not wait for all three. Reuse an already prepared immutable snapshot rather than reopening source content on timer resume.
4. Inspect **all three remote acceptance states before any launch decision**. Distinguish no remote script/root from transport failure. A failed or vanished accepted operation blocks new launches. An alive accepted controller with matching PID/start ticks means monitoring only. Lost SSH replies are uncertainty until authoritative remote acceptance can be queried; never infer `not_started` from an SSH error or missing local marker.
5. For each snapshotted root, bootstrap/transfer only before acceptance, or resume unready file transfer using the existing dataset lock/ready protocol. Check local template hashes before generating new roots and own generated source/plan fingerprints before every operation. Ready sets are immutable; skip them on resume. An interrupted unaccepted bootstrap can resume after its guard confirms there is still no acceptance; accepted roots must never receive source/manifest replacement.
6. Upload all newly completed sources independently of GPU availability or another task's training. After full transfer and hash verification, mark the source `ready_to_train`. Do not hold the shared GPU lock while exporting, uploading or waiting for predecessor.
7. Launch at most one ready root, using fixed priority among the currently ready roots; an incomplete earlier GPT source does not block a completed later one. Before launch, ensure all earlier **accepted** work has validated success and no failed/uncertain acceptance exists. The per-root remote launch independently rechecks the fixed Huangjin prerequisite and atomically acquires the shared GPU lock. `operation_locked` before acceptance is a retryable waiting condition; an accepted failure/uncertainty is fail-stop.
8. Subsequent ticks only monitor accepted roots. Do not resubmit `launching`, `running`, `failed` or uncertain stages. On completed state, verify exit/artifact hashes remotely, record remote final location and checksums in local metadata only, then permit the next ready root. All final and epoch weights remain on the GPU host.

### Minimum meaningful synthetic validation

- Only the three exact fixed owner/run IDs can be selected; incomplete sources never export, and terminal completion with zero retained images does not train.
- One completed source uploads while other sources still run; its training can begin after verified readiness without waiting for all three.
- Corrupt/partial transfers cannot publish readiness or launch. Already ready data and accepted source/plan bytes never change on timer rerun.
- Two competing root launches cannot both become accepted; orphan controller/trainer children retain both lock descriptors.
- Huangjin plan/prepared/queue/exit/artifact corruption blocks launch. New plan hashes change if predecessor identity changes, and the GPU lock path stays the fixed 1109 path.
- Lost launch response followed by a timer restart reattaches without a duplicate start. Dead/missing accepted identity blocks all further training.
- Timer reruns never invoke a model-download/backup command, and only metadata appears in its public output.
- Reuse existing pipeline/controller/predecessor tests where practical; synthetic fixtures only. Run targeted Ruff E/F/I/UP/B, Python 3.12 target, 100 columns, and compilation. No Python type checker is configured.

## Related specs and external references

- `.trellis/spec/backend/lora-training-contract.md`, especially accepted-operation immutability, fixed predecessor, GPU lock inheritance and fail-stop rules.
- `.trellis/workflow.md`: research artifacts persist under the supplied task; do not mutate accepted operations or application code as part of this research.
- No external references needed: existing Python/systemd primitives and reviewed project sources cover this bounded integration. No dependencies or runtime versions were queried in this research.

## Caveats / Not Found

- No production DB/content, private logs, model files, SSH/GPU, or live timer state were accessed.
- This report is design/source evidence only, not proof of deployed scheduling, actual source completion, upload, or training.
- Supplied run IDs, triggers, predecessor plan hash, owner and completion are parent/operator scope facts; the implementer/main must validate metadata at execution.
- Default local complete staging (`ops.stage`) avoids the backup call and is an alternative for each single-job root, but incremental readiness gives clearer immutable upload resumption and already has the needed dataset-receiver lock tests. Do not build a dynamic generic queue/framework to implement this fixed three-run request.
