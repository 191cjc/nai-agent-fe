# Shipov3 style, Longzhu and latest Moyan2 LoRA training

## Goal

On `root@i-1.gpushare.com:15571`, train one mixed style LoRA named
`aoqishipov3`, then independently train the `gpt龙主` character with trigger
`aoqilongzhu`. The operator subsequently requested appending the latest
`gpt末炎2` with trigger/output stem `aoqimoyan` after Longzhu. The operator
explicitly requested starting this batch. Existing
session authorization covers task registration and execution; no new approval
pause is needed for this established workflow.

## Fixed source selection

| Role | Dataset | Run ID | Available images |
| --- | --- | --- | ---: |
| style | swimv3 | 30a96ebe-76a8-4ab7-aedf-5781a03465cc | 99 |
| style | maidv3 | b34417b3-e174-4b15-82e7-04e743b73f65 | 82 |
| style | mikov3 | 302b6079-2d92-45dc-be11-c3d1da29fd71 | 89 |
| style | bikiniv3 | 5f814c35-225d-401a-9de6-961bc07e39b0 | 193 |
| style | kimonov3 | 05670d0d-d553-4216-b8f9-14ccd70f5cb0 | 96 |
| style | ndv3 | 248684e0-33c7-4669-94a2-f6861d7fda38 | 96 |
| character | gpt龙主 | 190849e1-ced3-449d-9c24-9c0406b68046 | 132 |
| character, last | gpt末炎2 | 4bb3a579-ce50-424d-8ffd-3e126cd12f7e | 127 |

The original seven populated runs are completed and have no unexpected missing retained
images. Exclude the stopped empty `bikiniv3` run
`a176aa6b-f0de-4b08-8ee4-501b03e379b4`. Export uses the latest owner-scoped
discard/purge/caption-override state and records count changes. Do not regenerate
failed groups. Initial counts are style 655, character 132.

Latest Moyan2 is pinned by run creation time and exact display name, not the
older `gpt末炎` runs. It is completed with 138 generation jobs: 127 succeeded,
11 failed. All 127 successful images remain usable, with no discards/purges or
missing retained files. Do not regenerate failures.

## Requirements

- Mix exactly the six selected style sources into one dataset, preserving their
  proportions and image/caption pairing. Shuffle actual training samples every
  epoch so clothing sources do not form consecutive source batches.
- Style trigger and final output stem: `aoqishipov3`; character trigger and output
  stem: `aoqilongzhu`. Exact final filenames are `aoqishipov3.safetensors` and
  `aoqilongzhu.safetensors`.
- Strict order: style first, Longzhu second, latest Moyan2 last. Moyan2's exact
  final filename is `aoqimoyan.safetensors`. Each starts independently from the
  same hash-pinned NoobAI-XL v1.1 base, never from the style LoRA's weights.
- Read only dataset metadata. Dedicated authorized export/training programs may
  consume and transfer private content; assistants never inspect real images,
  references, captions, private prompts/logs or safetensors metadata headers.
- Prepare local snapshots, then start style as soon as its remote files pass
  complete checksums. Continue character upload during style training.
- One detached GPU trainer; explicit per-job readiness and immutable accepted
  code/data; true exit/artifact validation before advancing; failure stops later
  training. Automatically retain epoch weights and back up verified final files.
- Preserve prior local results, source datasets and unrelated instance data.
  This request does not call for deleting existing weights or releasing the GPU.
- Upload Moyan2 while current training continues. Preserve the accepted two-job
  operation's source, plan, queue, readiness, data and live trainer. A separate
  appended stage must verify successful predecessor completion and share the
  predecessor's GPU exclusion lock before training; predecessor failure stops it.

## Acceptance

- [x] Original export manifests contain exactly the seven fixed populated runs, with
  current usable counts and no private content in diagnostics.
- [x] Synthetic and installed-source evidence proves pair-preserving sample
  mixing and actual per-epoch shuffling.
- [x] New RTX 3090 host has working CUDA/dependencies and the pinned base hash.
- [x] Actual style trainer is active under the exact requested output name;
  character upload can proceed concurrently and waits only for its own readiness.
- [x] Style and Longzhu both succeed in order, final/epoch artifacts validate and
  both exact final filenames have checksum-verified local backups.
- [x] Latest Moyan2's 127-image snapshot is privately exported/uploaded and fully
  checksum-verified while the existing queue continues.
- [x] Moyan2 starts automatically only after successful style and Longzhu,
  produces the exact final filename, and has a verified local final backup.

## Post-completion operator instruction

After all training and backup acceptance gates passed, the operator requested
deleting the project-server backups and no further backups. This supersedes the
earlier automatic-backup requirement. Only this batch's three backup weights
and checksum sidecars were removed; all three training-server final weights
remain. Do not recreate backups or automatically back up later LoRAs unless asked.
