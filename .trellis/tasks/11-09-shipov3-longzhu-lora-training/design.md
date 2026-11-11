# Design

Reuse the independently reviewed incremental training operation under
`/home/ubuntu/lora-kit/aoqi_training_1108/`, copied into the isolated
`/home/ubuntu/lora-kit/aoqi_training_1109_v3/`. Keep the previous operation intact.
New operation identity: `aoqi_training_1109_v3`; remote root:
`/hy-tmp/aoqi_training_1109_v3/`; local final backups:
`/home/ubuntu/lora-output/aoqi_training_1109_v3/`.

Change only fixed job metadata, operation/default connection/output paths and
exact final output stems; adapt operation-specific synthetic tests to the new
two-job plan. Retain the verified private exporter, owner/discard/purge logic,
paired deterministic filename mixing, per-job readiness, immutable receiver
locks, detached controller, true subprocess/final-artifact checks and retries.
Do not add a general scheduler or change the web/API application.

Use the existing public toolchain archive/tokenizer cache and setup scripts to
provision the fresh GPU host. The preinstalled CUDA Torch is 2.9.1+cu128; keep it
pinned while installing sd-scripts requirements. Base model URL and SHA-256 are
the existing verified NoobAI-XL v1.1 configuration. Only main performs SSH and
production export/transfer/start. Raw setup/export/training logs remain private.

Baseline matches prior successful jobs: 1024 buckets, batch 4, 12 epochs, save
every 2 epochs, UNet-only rank 32/alpha 16, AdamW lr 1e-4, cosine schedule, bf16,
gradient checkpointing and SDPA. The previous training used about 13 GiB, within
this host's 24 GiB. Style repeats 1; character repeats 3. Validate actual CUDA
startup and use metadata to distinguish loading from completed training.

Local snapshots are prepared before training. Bootstrap only immutable metadata,
then upload/verify style first; the detached controller waits for its readiness
and starts it immediately. Upload/verify Longzhu while style runs. Both start
from the base independently. Pipeline completion counts both jobs and backs up
their exact final filenames. Never overwrite accepted source or ready datasets.

No destructive cleanup is required on this fresh host. Preserve existing data;
uncertain accepted stages do not auto-retry. Transport interruption resumes only
unready transfers. Do not automatically release the instance.

Provisioning overlap: after export and immutable bootstrap, standalone `upload`
may begin before the base download completes. Once the complete base SHA and
CUDA/dependencies validate, `start` can accept the controller while that uploader
continues; its receiver/readiness locks are independent of controller/GPU locks.
After standalone upload exits, `background` reattaches to accepted status and
resumes any unready transfers before watching/backups. Main monitors standalone
upload exits because that CLI action has no transport retry loop. Independent
review approved this existing-CLI sequence; never start before base validation.

## Appended Moyan2 stage

The smallest new behavior is one additional independently trained character after
the accepted two-job prefix. Its queue cannot be edited in place: the live
controller pins immutable metadata. Create isolated operation
`aoqi_training_1109_moyan2` under `/home/ubuntu/lora-kit/`, remote
`/hy-tmp/aoqi_training_1109_moyan2/`, and backup root
`/home/ubuntu/lora-output/aoqi_training_1109_moyan2/`. Fixed job
`char_moyan2_gpt_1109` uses only run `4bb3a579-ce50-424d-8ffd-3e126cd12f7e`,
127 images, character repeats 3, trigger/output `aoqimoyan`, and the same baseline.

Reuse frozen source only into the new operation, never existing datasets or
runtime state. Expected changes are the new operation's fixed metadata/default
paths, a narrow predecessor gate/launcher, the shared GPU lock selection and
meaningful synthetic tests/README. Reuse existing exporter, per-job transfer,
readiness, launch-once, true-exit/artifact validation and final backup helpers.
Do not modify the original operation, application, global toolchain or base.

Pin predecessor root/operation, the accepted plan SHA
`61ecfcfca617cc94d0b79ee16d79dfb37f870259f44a704accf036703dd90486`, ordered
two-job queue and exact final names. Upload/verify the new dataset before waiting
for successful predecessor completion. A detached local launcher polls structured
predecessor status, retries transport errors, stops on predecessor failure or
uncertainty, verifies its successful final artifacts, and attaches/starts the new
reviewed workflow once. The new remote controller independently enforces that
predecessor condition and shares `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`, with
lock inheritance to its trainer. Never treat idle GPU or process disappearance
alone as successful predecessor completion, or rewrite/restart accepted work.

Tests must establish upload-before-wait, exact selection/trigger/name, pending and
failed/corrupt/mismatched predecessor rejection, no duplicate launch on lost
transport replies, shared GPU exclusion/orphan locks, and a verified final-only
backup for the new operation. Main owns all production metadata/export/SSH/start;
implementer and checker use only source and synthetic fixtures.
