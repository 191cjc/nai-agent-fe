# Runtime handoff — 2026-11-09 12:25 Asia/Shanghai

- Operation: `aoqi_training_1109_v3`; endpoint `root@i-1.gpushare.com:15571`.
- Source/runtime: `/home/ubuntu/lora-kit/aoqi_training_1109_v3/`.
- Remote: `/hy-tmp/aoqi_training_1109_v3/`.
- Final backups: `/home/ubuntu/lora-output/aoqi_training_1109_v3/`.
- Plan SHA-256: `61ecfcfca617cc94d0b79ee16d79dfb37f870259f44a704accf036703dd90486`.

Export completed with exactly 655 style and 132 character pairs, all seven fixed
run counts unchanged and discard/purge marks honored. The initial style filename
order mixes all six sources (largest consecutive source group: 4). Installed
source additionally shuffles bucket members and batch indices each epoch.
Independent review passed 36 synthetic tests, Ruff and compilation; original
1108 operation source remains unchanged. No private content/logs were inspected.

Provisioning exited 0. RTX 3090 24 GiB; Torch 2.9.1+cu128; CUDA matrix operation
passed; trainer CLI import exited 0. The downloaded base is 7,105,349,958 bytes;
the accepted controller verified SHA-256
`6681e8e4b134c81f16533acedb0d406d7e5e366e1624b4105178c64d00b05d51`.

Remote controller PID 7882 / start ticks 34975037 is alive. Its state is
`running`, with style `waiting_data` and Longzhu `pending`. **No actual GPU
training has started yet.** Last remote transfer metadata: 324/655 style PNGs,
401,134,685 image bytes; no ready marker yet. The incremental uploader publishes
readiness only after complete image/caption checksums; controller begins style
then, while later Longzhu upload continues. The two jobs use the base independently.

The standalone upload PID is 3414197, exec session 36466. Detached handoff PID
3418498 / start ticks 812721800 is alive and holds `.handoff.lock`; its metadata
state is `waiting_upload`. It blocks on the local `.transfer.lock`, releases that
descriptor immediately when the uploader completes or fails, and invokes
`ops.py background`. It checks exit/JSON response plus the returned child PID's
start identity and inherited background lock. Errors remain private and static
codes go to handoff_status.json. The handoff has been source-reviewed; it is
runtime orchestration and does not modify accepted remote code or data.

Do not start another uploader/background/handoff during that transition. Existing
background workflow reconnects, resumes only unready data, preserves the accepted
controller, stops after real trainer failure, and automatically verifies/backups
both exact final filenames. Do not rerun setup or change accepted source/datasets.

Safe status: `python3 /home/ubuntu/lora-kit/aoqi_training_1109_v3/ops.py status`.
Safe records: provision_status.json, stage_status.json, remote_status.json,
handoff_launch.json, handoff_status.json, workflow_launch.json,
workflow_status.json and backups.json. Never read `*.private.log` or dataset/model
content. On a transport error, do not mistake the CLI's local failure record for
remote training failure; reconnect to structured remote status.

Both training completions, exact final files and two verified local backups are
still outstanding. Keep the task active until these acceptance gates pass. No
deletion, server release, app change or commit was performed.

# Verified live training — 2026-11-09 13:24 Asia/Shanghai

Style actually started at 12:45:32 (trainer PID 8436), with controller PID 7882 alive. GPU utilization is 100%, using 12,724 MiB of 24,576 MiB. Style epoch 2 and 4 checkpoints each have 170,602,108 bytes; epoch 4 was saved at 13:18:40. No final weights yet.

Both datasets are ready. Style readiness was published before training, and Longzhu readiness at 12:54:51 was published after style had started: real upload/training overlap is verified. Detached handoff completed successfully; background workflow PID 3425855 is alive, watching and will back up validated finals. Longzhu remains pending behind style.

Observed epoch 2→4 interval is 819.3 seconds (~409.7 seconds/epoch). Linear style completion is around 14:13; operator estimate includes a margin: style ~14:15–14:30, both jobs and backups ~15:15–15:45 Beijing time. Character estimate scales the same settings from 655 style samples to 132×3 character samples and remains provisional until actual character checkpoints. Task stays in_progress.

# Appended latest Moyan2 ready — 2026-11-09 14:34 Asia/Shanghai

The operator requested the latest exact-name `gpt末炎2`, trigger `aoqimoyan`,
last after Longzhu. Pinned completed run: `4bb3a579-ce50-424d-8ffd-3e126cd12f7e`.
Of 138 generation jobs, 127 succeeded and 11 failed; 127 retained images remain
usable with no marks or missing files. Failed generations were not rerun.

The original accepted two-job queue/source/data were preserved. A separate fixed
operation now lives at `/home/ubuntu/lora-kit/aoqi_training_1109_moyan2/`, remote
`/hy-tmp/aoqi_training_1109_moyan2/`, final backups
`/home/ubuntu/lora-output/aoqi_training_1109_moyan2/char_moyan2_gpt_1109/`.
Its sole job is `char_moyan2_gpt_1109`, repeats 3, exact final
`aoqimoyan.safetensors`, same base and character baseline. Exporter remained
byte-identical; all 14 pinned original source/immutable metadata files remained
unchanged. Independent review passed 39 synthetic tests, Ruff and compilation.
The reusable code-spec records the predecessor and inherited GPU-lock contracts.

Main exported 127 paired files (205,855,585 total bytes), bootstrapped reviewed
immutable metadata and launched detached workflow PID 3446399 / start ticks
813431787. All 127 image/caption pairs were uploaded and fully hash-verified;
remote readiness was published at 14:32:24 (1794205944.7949643), while Longzhu
was actively training. Plan SHA is
`324a84bee7f31602a7467047d44cee0c2ea38786affa645f1e440d7a3926b0d5`;
manifest SHA is
`2b3df855281ca487aea76ceae2addc6ffddfa63e1dc25c5276a80944d2853832`.

New workflow is alive in `waiting_predecessor`, with
`predecessor_in_progress`; it holds no GPU lock while waiting. It will verify
fixed predecessor identity, both recorded zero exits and all final/epoch hashes,
then start once under the same inherited `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`.
Remote launch/controller independently enforce the same condition. It retries
transport failures and backs up its exact verified final automatically. Failed
or uncertain predecessor/training states stop the tail rather than retraining.

Original style succeeded at 14:13:29 with exit 0; its final
`aoqishipov3.safetensors` (170,602,108 bytes; SHA
`c79e6a959d37e112ea41c0f4f22a3fa0ca87e24c5a7d5a71893a1d249da32c1b`)
is already backed up under the original output root. Longzhu started at 14:13:30
and has epoch-4 checkpoints at this update. Moyan2 is uploaded and queued, not
training yet. The earlier two-job ETA does not cover this appended third job.

For future status, inspect BOTH operation roots' structured workflow/remote status
and backup metadata. New safe CLI:
`python3 /home/ubuntu/lora-kit/aoqi_training_1109_moyan2/ops.py status`.
New safe queue records also include `predecessor_status.json` and staged readiness.
Do not rerun setup, edit accepted source/data/queues, start a competing workflow
or read private logs/content. Task remains in_progress until all THREE exact
final weights have succeeded in order and have verified local backups (two in
the original operation plus one in the appended operation). No deletion,
instance release, app change or commit was performed.

# All three completed — 2026-11-09 16:04 Asia/Shanghai

Final metadata confirms both operations are `completed`, all three jobs are
`succeeded` with exit code 0, and every exact final file has a checksum-verified
local backup. A fresh local SHA-256 pass matched all three backup records.

| LoRA | Training completed (Beijing) | Local final backup |
| --- | --- | --- |
| aoqishipov3 | 14:13:29 | `/home/ubuntu/lora-output/aoqi_training_1109_v3/style_shipov3_1109/aoqishipov3.safetensors` |
| aoqilongzhu | 15:05:28 | `/home/ubuntu/lora-output/aoqi_training_1109_v3/char_longzhu_gpt_1109/aoqilongzhu.safetensors` |
| aoqimoyan | 15:56:15 | `/home/ubuntu/lora-output/aoqi_training_1109_moyan2/char_moyan2_gpt_1109/aoqimoyan.safetensors` |

Moyan2 started at 15:06:42 after successful predecessor validation. The original
workflow finished its backups at 15:07:22; the tail workflow finished its backup
at 15:57:48. Final evidence is in `research/final-completion.json`. Final files
represent epoch 12; retained intermediate checkpoints end at epoch 10 as expected.

Live remote metadata at this check reports GPU utilization 0%, memory 1/24576 MiB,
and completed controllers. There is no remaining training or backup wait in this
three-job batch. All training acceptance criteria are fulfilled. No private
content/logs or model headers were inspected; no instance release or deletion
was performed. Task bookkeeping remains unarchived pending the normal commit
workflow; this does not affect completed training or saved outputs.

# Operator-requested backup cleanup — 2026-11-09T16:11:55.888628+08:00

The operator clarified that backups on the project server are not wanted. Deleted
only this batch's three local final model backups and six checksum sidecars under
`/home/ubuntu/lora-output/aoqi_training_1109_v3/` and
`/home/ubuntu/lora-output/aoqi_training_1109_moyan2/`. Both directories are now
absent. Before cleanup, confirmed all three exact final weights still exist on
`root@i-1.gpushare.com:15571` with matching file sizes. The completed background
workflows hold no live lock and will not continue downloading. Remote outputs,
source datasets and unrelated files were preserved. Do not restart backup
workflows or automatically back up later LoRAs unless the operator asks. Earlier
backup/hash evidence is historical; `research/backup-cleanup.json` records the
current absence of these local backups.
