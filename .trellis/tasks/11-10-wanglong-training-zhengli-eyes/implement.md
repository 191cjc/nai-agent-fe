# Execution plan

- [x] Present concrete plan and receive operator approval.
- [x] Inspect source, dataset metadata, GPU, dependencies and base hash.
- [x] Implement isolated one-job operation with existing readiness/fail-stop rules.
- [x] Run synthetic pipeline/controller/ops tests, targeted Ruff and compilation.
- [x] Independent Trellis check of exact selection/output, baseline and shared lock.
- [x] Prepare Wanglong snapshot privately; verify counts/hashes without viewing data.
- [x] Bootstrap/upload/verify, start one detached trainer and backup monitor.
- [x] Verify live PID/start identity, GPU activity and checkpoint progress metadata.
- [x] Remove Zhengli diagnosis following the operator cancellation.
- [x] Stop local automatic backup workflow following the operator cancellation;
  verify no local weights have been downloaded and remote training stays alive.
- [x] Record live-training evidence and first epoch-2 checkpoint metadata.
- [x] Verify final remote exit/artifacts/checksums when available; no local backup.
- [x] Prepare/review independent Huangjin staging source and synthetic checks.
- [x] Privately export and verify 123 Huangjin pairs without viewing content.
- [x] After verified Wanglong success, stage Huangjin remotely without training
  or local backup; verify pair counts/hashes and absence of a trainer.
- [x] Launch the reviewed Huangjin trainer following the operator clarification;
  verify actual trainer PID/start identity and GPU activity. No local backup.
- [x] Verify Huangjin final remote exit/artifacts/checksums when available.
- [x] Research/review minimal durable three-run timer pipeline using fixed
  independent operation roots and existing private exporter/trainer protocols.
- [x] Implement/check scheduler, source templates, synthetic tests and systemd
  units; preserve accepted operations and prevent any local weight download.
- [x] Install and enable the timer; verify its live poll/status and metadata-only
  source selections, upload/launch behavior when a source is ready.
- [x] Record scheduler runtime evidence and the durable operation contract.

## Five-run extension

- [x] Confirm added Yinzhi/An owner, names, GPT lane, IDs and status using metadata.
- [x] Stage only reviewed source/tests/units; preserve running data and processes.
- [x] Append the two fixed inputs; update release/docs and focused synthetic checks.
- [x] Independently check the complete staged operation; preserve all templates.
- [x] Promote checked files while leaving the active upload/trainer running;
  restore the enabled timer and verify immutable original snapshots and live health.
- [x] Record five-run deployment/first-poll metadata and update the contract.

In the new operation run application-venv `python -m unittest -q test_pipeline
test_controller test_ops`, Ruff E/F/I/UP/B with Python 3.12 and 100 columns,
and compilation. Use disposable synthetic fixtures only. No type checker is
configured. Production observations are structured status, PID/start ticks,
counts, filenames, sizes, timestamps and hashes.

Change boundary: new operation source/tests only; no application changes, source
dataset edits, base changes or accepted queue rewrites. Main alone operates the
GPU and private exporter. No destructive cleanup or uncertain-training retry.
