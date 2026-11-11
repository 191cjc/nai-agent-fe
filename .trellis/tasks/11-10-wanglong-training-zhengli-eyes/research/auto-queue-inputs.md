# Fixed automatic pipeline inputs

These are the original three inputs. The operator subsequently approved exactly
two additions in `auto-queue-added-inputs.md`; the deployed current scope is five
runs, verified in `auto-queue-five-run-runtime.json`.

Latest user instruction authorizes an actual durable timer and automatic export,
upload and training, without additional per-run approval. No local model backup.

- Owner: `48fd7397-53cc-422a-8bac-69293871848c`.
- Source DB: `/var/lib/novelai/novelai.sqlite3` (read-only); images storage:
  `/var/lib/novelai/generation-images`. Only the dedicated exporter reads content.
- Selected source lane: `gpt`. No unrelated NovelAI/style generation is selected.
- `gpt死令`: `11fde849-209e-4fd0-85d1-15f14a2c875a`, trigger `aoqisiling`,
  priority 1. Running at first poll: processed 106/138, success 101, failed 5.
- `gpt正理`: `16dd3f0f-1a8a-4a03-abe6-569f462051d6`, trigger `aoqizhengli`,
  priority 2. Running at first poll: processed/success/failed 0/0/0 of 138.
- `gpt博加丘`: `916a6dd9-74fe-4e69-b876-a7a1725ea275`, trigger `aoqibojiaqiu`,
  priority 3. Running at first poll: processed/success/failed 0/0/0 of 138.
- Remote: `root@i-1.gpushare.com:15571`, identity
  `/home/ubuntu/.ssh/gpushare_ed25519`, IdentitiesOnly and BatchMode required.
- Local scheduler source root: `/home/ubuntu/lora-kit/aoqi_auto_1110_gpt`.
- Dedicated systemd names: `aoqi-auto-1110-gpt.service` and `.timer`.
- GPU lock: `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`.
- Completed fixed predecessor: `/hy-tmp/aoqi_training_1110_huangjin`, operation
  `aoqi_training_1110_huangjin`, plan SHA-256
  `8320c7e3d74fc560d43a5b969405eebc9a87faea8836491f366eb06de5cf13a9`.
- Predecessor sole job/trigger: `char_huangjin_gpt_1110` / `aoqihuangjin`;
  final `aoqihuangjin.safetensors`, 170545012 bytes, SHA-256
  `70e96467dfd1f5812b4c88e674b6eeb27e5bf29029d3ff51c78e550044ef8a66`.
- Huangjin structured status is completed, job succeeded, exit 0, six remote
  artifacts. Remote hashes must be revalidated by the launch gate.
- Systemd is available locally. Main owns deployment, DB metadata and SSH.
  Implement/check agents use source and synthetic fixtures only.

Privacy: never view images, reference assets, caption files, private prompt or
settings DB columns, raw private logs or model headers. Names/IDs/counts/sizes/
timestamps/schema/status/hash metadata only. No existing accepted operation edits.
