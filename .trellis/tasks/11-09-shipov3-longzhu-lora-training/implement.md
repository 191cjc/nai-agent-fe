# Execution plan

- [x] Operator explicitly requested starting the two-stage batch on port 15571.
- [x] Inspect metadata only: pin seven completed populated runs; exclude empty
  same-name run; confirm 655 style / 132 character images and no missing files.
- [x] Inspect fresh host: RTX 3090 24 GiB, Torch 2.9.1+cu128/CUDA available,
  50 GiB free data volume, no preinstalled base/training repository.
- [x] Activate this task and dispatch implement/check agents with curated spec
  context. Main owns task records and every production operation.
- [x] Reuse the reviewed incremental operation in a new isolated directory with
  exact two-job plan/output stems/default endpoint; run meaningful synthetic
  tests, targeted Ruff and compilation; independent review must pass.
- [x] Provision the new host using existing setup scripts, public source/cache
  archives and hash-pinned base download while preparing training snapshots.
- [x] Run authorized private exporter, recording only counts/sizes/checksums;
  publish local incremental metadata and bootstrap reviewed source/manifests.
- [x] Start one detached style-first controller/upload workflow. Verify real
  style process/GPU activity and concurrent character upload where applicable.
- [x] Monitor metadata; after each successful validated stage, back up exact final
  weight/checksums. Record both completed results and retain per-epoch weights.

Final original runtime: style succeeded at 14:13:29 and Longzhu at 15:05:28
Asia/Shanghai on 2026-11-09, both with exit code 0. Both exact final files and
epoch artifacts were validated. The original workflow completed at 15:07:22
with both final files backed up locally. See progress.md and
research/final-completion.json for final metadata and hashes.

## Appended latest Moyan2

- [x] Operator requested latest `gpt末炎2`, trigger `aoqimoyan`, last in order.
- [x] Metadata pins completed run `4bb3a579-ce50-424d-8ffd-3e126cd12f7e`:
  127 usable images; 11 generation failures; no unexpected missing retained files.
- [x] Implement isolated new operation and narrow successful-predecessor gate,
  preserving every original accepted source/metadata/data/result byte.
- [x] Independent synthetic/lint/compile review passes, including shared GPU lock
  exclusion, fail-stop dependency and launch-once/reconnect behavior.
- [x] Main privately exports, bootstraps, uploads/verifies and starts the detached
  appended workflow while current training continues; verify waiting/status.
- [x] All three final weights succeed in order and have verified local backups.

Moyan2 automatically started at 15:06:42 after predecessor validation and
succeeded at 15:56:15 with exit code 0. Its final backup completed at 15:57:48.
All three local finals were independently hashed again and matched their
recorded remote artifact and backup checksums. No training remains pending.

Validation: synthetic-only unittest modules, Ruff E/F/I/UP/B (Python 3.12 target,
100 columns), Python compilation; type checker is not configured. Verify installed
loader/bucket epoch shuffle from source only. Never open dataset content or raw
private logs. Stop on real failure, distinguish transport interruption, and do
not declare success based only on an accepted process or epoch checkpoint.
