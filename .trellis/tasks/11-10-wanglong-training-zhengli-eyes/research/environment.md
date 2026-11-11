# Read-only environment evidence

Collected 2026-11-10; no private training content was inspected.

- Dedicated `/home/ubuntu/.ssh/gpushare_ed25519` authenticates to
  `root@i-1.gpushare.com:15571`; default identity fails.
- GPU RTX 3090 24,576 MiB, initially idle; `/hy-tmp` free about 40 GiB.
- Python 3.11.12, torch 2.9.1+cu128, accelerate 1.15.0, diffusers 0.40.0,
  transformers 5.17.0, safetensors 0.8.0. Offline sd-scripts/LoRA imports,
  CUDA and bf16 pass. Both CLIP tokenizer cache directories exist.
- Base size 7,105,349,958, verified SHA-256
  `6681e8e4b134c81f16533acedb0d406d7e5e366e1624b4105178c64d00b05d51`.
- Reuse source only from `/home/ubuntu/lora-kit/aoqi_training_1109_v3`:
  `common.py`, `prepare.py`, `remote_train.py`, `ops.py` and synthetic tests.
- Shared GPU lock `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`. November 9 style,
  Longzhu and Moyan2 operations completed and final backups verified.
- Wanglong completed run `2bfd3586-5c15-49ab-abe9-91fa52caa083`: 134 successes,
  4 failures, 134 retained files, zero discard/purge marks.
- Recent Zhengli run `ef49378c-ac5d-4f8e-a320-2a8443e49559`: 138 files. Final
  November 8 backup is 170,545,332 bytes, SHA-256
  `b92e04dc447f0034139151be36938f69162f86a3648caca2d909632a8e3d5363`, stem
  `aoqizhengli_noobai`. Older script uses `zhengli_gpt_noobai`, trigger `zhengli`.

Privacy: never inspect `img/`, captions, actual DB settings/prompt text, private
logs, image bytes or model headers. Source code and synthetic fixtures are safe.
