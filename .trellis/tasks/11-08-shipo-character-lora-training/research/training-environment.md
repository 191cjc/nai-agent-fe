# Read-only training environment findings — 2026-11-08

All evidence below is source code or permitted metadata. No training images, references, captions, prompt text, raw training logs, dataset exports or model metadata headers were inspected.

## Existing tooling

- `/home/ubuntu/lora-kit/README.md`: toolchain, SSH key identity, NoobAI base, detached job usage, output retention and known pitfalls. Trigger convention is also in `apps/web/README.md:52`.
- `/home/ubuntu/lora-kit/train_template.sh:13`: installed baseline accelerate / NoobAI-XL UNet LoRA training; line 19 caption-token shuffling, line 23 batch=4 / epochs=12 / save every 2; rank=32, alpha=16, lr=1e-4.
- `/home/ubuntu/lora-kit/nuoya_gpt_aoqi_1107/build_dataset.py:60`: separate existing exporter variant handles `caption_overrides`; lines 69..71 only exclude discard marks, so new isolated exporter must explicitly handle `purged_images` too. It processes content privately; never return private rows/bytes to the assistant.
- Root `~/lora-kit/build_dataset.py` lacks caption override support. Root `lora_job.sh` also has raw-error-tail printing and global process-disappearance completion checks; do not inherit those mechanisms into the new controller.
- Current local controller `/home/ubuntu/lora-kit/nuoya_gpt_aoqi_1107/run_job.py` has empty `held_processes`. An older priority controller plan recorded PIDs 2817191/2718133 with start ticks; do not signal them without checking they still exist and match identities. Current process snapshot found only Nuoya controller and its lora_job child among these queue scripts.

## GPU host

- Host `root@i-1.gpushare.com`, port 56541, key `/home/ubuntu/.ssh/gpushare_ed25519`. Default SSH identity failed; explicit existing key succeeded.
- GPU name `NVIDIA GeForce RTX 4090`, memory 49140 MiB, initial used=12942 MiB, utilization=100%.
- Data root `/hy-tmp`; initial free about 17.2 GB. Existing base `/hy-tmp/models/NoobAI-XL-v1.1.safetensors`, size 7,105,349,958 bytes. Preserve base, installed environment and datasets.
- Active old job `/hy-tmp/char_nuoya_gpt_aoqi_1107`, trigger/output `aoqinuoya_gpt_noobai`, base NoobAI-XL, batch 4, rank32, 12 epochs. Initial PID snapshot: shell 706, accelerate 708, trainer 773 and data loader worker descendants. Must refresh identities at execution time.
- Initial inventory of old LoRA: 128 `.safetensors` under 22 old `/hy-tmp/<job>/output/` directories, 21,829,977,392 total bytes. Active training can add more. Enumerate after stopping and exclude base `/hy-tmp/models/` and new operation directory.
- Remote `rg` is unavailable. Use `grep` for installed-source inspection.

## Mixing evidence

- Installed `/hy-tmp/sd-scripts/train_network.py:1189` creates the training DataLoader; line 1192 sets `shuffle=True`.
- Installed `library/train_util.py` re-exports dataset classes from `library/dataset.py`.
- Installed `/hy-tmp/sd-scripts/library/dataset.py:284` bucket-manager shuffle uses `random.shuffle(bucket)`; `shuffle_buckets` at line 828 seeds with `self.seed + self.current_epoch`, shuffles batch/bucket indices at line 832 and bucket members through `self.bucket_manager.shuffle()` at line 833.
- Epoch-reset call site was verified from installed source during execution: `dataset.py:542` checks `epoch > self.current_epoch`, line 546 increments the epoch, and line 547 calls `self.shuffle_buckets()`. Thus the mixed subset is shuffled anew every epoch, in addition to DataLoader sampling. No dataset or raw log content was used to verify this.
- Preserve all seven selected styles in one subset; deterministic pair renaming plus epoch bucket/sample shuffle prevents source-file ordering from dictating training order. Caption token shuffle alone would not establish sample mixing.

## Source-data metadata

SQLite `/var/lib/novelai/novelai.sqlite3` is schema13. Read-only queries selected only names, run IDs/status/counters, job IDs/image_count, non-content experiment ID fields and discard/purge index metadata. File existence and size were checked by stat only. Selected counts: style 97+95+87+98+77+10+15=479; GPT roles 132,136,138. All ten populated runs completed and had zero unexpectedly missing eligible files. A same-name `识破gn` stopped run has zero images and is not selected. Exact IDs live in the PRD.

No source-group failures will be regenerated. Do not include other similar names/versions or unscreened unrelated runs. Export snapshots must read final discard/purge state at their own start and record count changes.
