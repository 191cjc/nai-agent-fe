# Wanglong and Huangjin character LoRA training

## Goal

Train the approved GPT Wanglong character LoRA. The operator approved the concrete
training summary with `是的`; approval covers creation and execution. The operator
subsequently cancelled Zhengli investigation; only Wanglong remains in scope.
The operator then explicitly cancelled local weight backup to conserve local
storage. Keep all checkpoints/final weights on the GPU server only.
The operator subsequently requested uploading `gpt黄金` after Wanglong finishes.
The operator then clarified that Huangjin training should start immediately;
the initial staging-only interpretation was too narrow. Launch the reviewed
Huangjin trainer with trigger `aoqihuangjin` and the Wanglong baseline.

## Confirmed facts

- Target: `root@i-1.gpushare.com:15571`, idle RTX 3090 24,576 MiB.
- Existing dependencies import, CUDA/bf16 work, tokenizer caches are present,
  and NoobAI base SHA matches the established pinned value.
- `gpt王龙`: run `2bfd3586-5c15-49ab-abe9-91fa52caa083`, owner
  `48fd7397-53cc-422a-8bac-69293871848c`; completed, 134 successes, 4 failures,
  134 retained files, zero discards/purges, 329,358,484 source bytes.
- Recent `gpt正理`: run `ef49378c-ac5d-4f8e-a320-2a8443e49559`, 138 images;
  `aoqi_training_1108` recorded 12 epochs, exit 0 and a verified final backup.
  Earlier scripted Zhengli run `423701c6-ccca-496e-8f24-7eae8f1c775a` is absent.
- November 9 operations completed and backed up; no active trainer/controller.

## Requirements

- R1: Start Wanglong first. Use exactly the selected completed run, honor current
  overrides/discards/purges, and never regenerate failed source groups.
- R2: Trigger/output `aoqiwanglong` / `aoqiwanglong.safetensors`. Independent
  NoobAI-XL v1.1: 1024 buckets, repeats 3, batch 4, 12 epochs, save every 2,
  UNet-only rank 32/alpha 16, AdamW 1e-4 and the established remaining baseline.
- R3: Separate operation with immutable manifests/readiness, shared GPU exclusion,
  detached remote execution, actual trainer exits and fail-stop. Keep weights
  remote only; no local backup/download. Preserve source data and existing outputs.
- R4: The operator cancelled Zhengli diagnosis; do not load, diagnose or retrain
  Zhengli. Preserve the approved Wanglong baseline. Huangjin training is the
  separately authorized extension in R6.
- R5: Assistants never read images/thumbnails/references, captions, DB prompt text,
  raw private logs or model headers. Dedicated authorized exporter/transfer/trainer
  programs alone process private data; their diagnostics remain private.
- R6: After verified Wanglong completion, upload exactly the completed `gpt黄金`
  run `d97531fa-5be1-4eba-9081-2e424b5e6bce`, owned by the same operator: 123
  succeeded images, 15 failed groups, zero discard/purge marks and no missing
  retained files at inspection. Do not regenerate failures. After uploading,
  start Huangjin training with the same baseline and remote-only weights.

## Acceptance criteria

- AC1 (R1–R3): Ready dataset identifies exactly 134 Wanglong pairs unless new
  operator marks change selection; missing source files fail safely.
- AC2 (R2–R3): Synthetic checks pass before launch; live PID/start identity and
  GPU/checkpoint metadata establish exactly one accepted trainer.
- AC3 (R3): Epoch/final weights remain remote, with remote checksum verification
  on successful completion. Local automatic backup is stopped and no weights are
  downloaded. Report startup and completion separately.
- AC4 (R4–R5): Work covers Wanglong and Huangjin training only, with no private
  training content exposed and no Zhengli investigation.
- AC5 (R6): A separate Huangjin root has 123 verified PNG/caption pairs uploaded
  only after Wanglong completes successfully. Exactly one detached Huangjin
  trainer starts using the reviewed baseline; no local result backup is started.

## Out of scope

Application changes, source caption edits, paid image generation, automatic
Zhengli retraining, deleting existing artifacts and releasing the GPU host.

## Automatic pipeline extension (latest operator request)

The operator explicitly requests a durable scheduled task for the three GPT
generation runs currently active. This authorizes automatic private export,
upload and character LoRA training for these exact IDs after generation ends:

| Run name | Run ID | Trigger |
| --- | --- | --- |
| gpt死令 | 11fde849-209e-4fd0-85d1-15f14a2c875a | aoqisiling |
| gpt正理 | 16dd3f0f-1a8a-4a03-abe6-569f462051d6 | aoqizhengli |
| gpt博加丘 | 916a6dd9-74fe-4e69-b876-a7a1725ea275 | aoqibojiaqiu |

Owner is `48fd7397-53cc-422a-8bac-69293871848c`. This authorizes the new Zhengli
training run; the earlier eye investigation remains cancelled. It supersedes
the earlier blanket exclusion of automatic Zhengli retraining for this new run.

- R7: Poll these fixed run metadata every 60 seconds using a durable systemd
  timer. Completed generation triggers export of retained successes only,
  preserving overrides/discards/purges; failed groups are never regenerated.
- R8: Upload and verify each completed dataset without waiting for all three.
  Train one ready character at a time using the same independent NoobAI baseline
  and shared GPU exclusion. Incomplete generation must not block another ready
  dataset. Continue after verified training success only; failed/uncertain accepted
  training halts launches. Transport recovery must not duplicate training.
- R9: Weights remain remote only. The new automation must have no local model
  backup path and must not invoke existing backup/watch/workflow behavior.
- AC6: The installed/enabled timer survives the session and reboot, selects
  only the three pinned owner/run IDs, and has a metadata-only status command.
- AC7: Synthetic checks prove completion gating, independent uploads, single
  training, duplicate prevention, failure/uncertainty stops, transport recovery,
  immutable accepted snapshots and no backup. Deployment establishes timer and
  first-poll health; report actual live states separately from synthetic results.

No application changes, extra generation jobs, unselected runs, destructive
cleanup or existing accepted source edits are included.

## Additional operator-selected GPT runs

The operator subsequently added `gpt音织` and `gpt安` to the same automatic
completion/export/upload/train timer. Append exactly these same-owner GPT runs
after the original three priorities; no further generation is requested:

| Run name | Run ID | Trigger |
| --- | --- | --- |
| gpt音织 | 5e49840f-5865-4c1c-9e03-247b1d3acd03 | aoqiyinzhi |
| gpt安 | 354f7cbc-4781-4b86-93d2-a300492fb932 | aoqian |

- R10: Extend the existing enabled timer to exactly five fixed runs, preserving
  all original run identities, frozen snapshots, upload progress and remote
  acceptance. Do not stop an active upload/controller/trainer to apply this
  extension. Keep all baseline, privacy, fail-stop and remote-only weight rules.
- AC8: Synthetic checks establish exact five-run selection and original snapshot/
  acceptance preservation. Reviewed source is installed into the existing timer;
  subsequent scheduled passes include the added runs without duplicate training.
