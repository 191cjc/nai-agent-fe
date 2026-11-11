# Validation and accepted launch

Implementation and independent review each passed all 38 synthetic tests in
`test_pipeline`, `test_controller`, and `test_ops`. Full operation Ruff
E/F/I/UP/B (Python 3.12, 100 columns) and seven-file compilation pass. No Python
type checker is configured. No application code changed; application checks
were not needed. All tests use synthetic fixtures, fake transports and trainers.

Review found only a README example GID mismatch; corrected to actual GID 1001
and isolated absolute-path sudo invocation. The four production source files
remained unchanged after review. `prepare.py` equals the reviewed v3 exporter.

Production preparation completed with exactly 134 Wanglong pairs, no discarded
or purged items, and the selected completed run only. All local pair sizes and
hashes verified before publishing immutable queue metadata. Bootstrap succeeded.
Detached local workflow accepted PID 3782546; transfer, single remote launch,
monitoring and final-only checksum-verified backup are handled by reviewed ops.
A launched workflow is not evidence of a started or completed trainer.

Existing LoRA training contract was reviewed: the new operation retains existing
CLI, storage, readiness, shared GPU lock and backup contracts. No new spec
behavior or application API contract was introduced. Zhengli work was cancelled.

Safe status command:

```sh
/home/ubuntu/nai-agent-fe/apps/api/.venv/bin/python /home/ubuntu/lora-kit/aoqi_training_1110_wanglong/ops.py status
```

Do not read private logs, images, captions, source prompt fields or model headers.

Production startup confirmed: all 134 PNG/caption pairs transferred (194,460,867
bytes), immutable readiness published, live controller PID 1209/start ticks
44396786 and trainer launcher PID 1613/start ticks 44480137. Training accepted
at epoch timestamp 1794292918.174699. Trainer child PID 1678 is present; GPU
memory/use grew during startup. No checkpoint or successful exit claimed yet.
The detached local workflow continues monitoring and final-only backup.

## Operator override: remote weights only

The operator explicitly cancelled local backup after startup. Identity-checked
local workflow PID 3782546 was stopped with SIGTERM; its process is no longer
alive. The local backup directory contains zero files and zero weights. No
accepted source, dataset, queue, remote controller or trainer was changed.
Do not restart `backup`, `watch`, `workflow` or `background`: frozen ops source
retains its original local backup behavior. Use `status` only for observations.

Remote metadata at epoch timestamp 1794293521: state running/training, trainer
PID 1613 alive, GPU 13,612 MiB / 100%, epoch-2 checkpoint present. Its metadata:
`aoqiwanglong-000002.safetensors`, 170,545,284 bytes, mtime 1794293518.052189.
Output directory remains
`/hy-tmp/aoqi_training_1110_wanglong/jobs/char_wanglong_gpt_1110/output`.
Training is still in progress; no final exit or final artifact is claimed.
