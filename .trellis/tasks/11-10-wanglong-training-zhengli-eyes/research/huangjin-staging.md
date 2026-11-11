# Huangjin staging metadata and boundary

Operator requested uploading `gpt黄金` after Wanglong finishes. No Huangjin
training launch or local weight backup is authorized. The trigger is reserved
as `aoqihuangjin` by the existing character naming convention.

- Source run: `d97531fa-5be1-4eba-9081-2e424b5e6bce`.
- Owner: `48fd7397-53cc-422a-8bac-69293871848c`.
- Display name: `gpt黄金`; completed; total 138 groups, 123 succeeded/15 failed.
- Retained files: 123, missing 0, discard/purge marks 0; source bytes 353,917,884.
- No private source/settings/caption/image contents were inspected. The SQL
  queries emitted names, IDs, status/counts and filesystem metadata only.
- New local root: `/home/ubuntu/lora-kit/aoqi_training_1110_huangjin`.
- New remote root: `/hy-tmp/aoqi_training_1110_huangjin`.
- Job: `char_huangjin_gpt_1110`; trigger `aoqihuangjin`; expected pairs 123.
- Source-only clone from frozen Wanglong source; keep private exporter byte
  identical and retain existing protocol/locks. Only identity/default paths
  and corresponding test fixtures should change.
- Complete-transfer `ops.py stage` has no launch or backup call. Do not run
  other actions except `status` for this staging-only extension.
- Main owns production export and SSH. Agents own the new source/README/tests
  and synthetic checks only. Do not modify Wanglong source, data or plans.
- Main must verify Wanglong completed with successful exit/artifacts/checksums
  before initiating the Huangjin transfer.

## Checks and preparation

Implementation and independent Trellis review each passed all 38 synthetic
tests, targeted Ruff E/F/I/UP/B (py312, 100 columns) and seven-file compilation.
No Python type checker is configured. The only review fix clarified an inherited
queue comment. Production four-file source is frozen; hashes are recorded in
`huangjin-source-manifest.json`. The exporter and remote controller remain byte
identical to the reviewed Wanglong versions. The stage regression rejects backup
and trainer launch calls. No application code or new protocol behavior changed;
the existing training contract applies without a spec addition.

Private export succeeded with exactly 123 pairs, no changed selection, discarded
or purged files. Wanglong completed with exit 0 and all six recorded remote model
sizes/hashes were revalidated before the Huangjin `stage` command was invoked.
See `wanglong-completion.json`; the final SHA-256 is
`233c88496fdb182c220df7725fbbffe9f59954d27623e3f9034f5fa47a64c3ef`.

## Remote transfer result

Complete-transfer stage succeeded. A separate remote verification rehashed all
pairs against the manifest: 123 PNG + 123 caption files, 206,024,328 bytes. Plan
SHA-256 is `8320c7e3d74fc560d43a5b969405eebc9a87faea8836491f366eb06de5cf13a9`.
Remote controller status remains `not_started`, with no accepted status/launch
marker and zero model files. Both Wanglong and Huangjin local backup directories
contain zero files/bytes. No model content/header/private diagnostics were read.
The training and upload acceptance criteria are satisfied; no Huangjin training
was launched. See `huangjin-transfer.json` for structured evidence.

## Operator clarification: start Huangjin training

The operator asked why training had not started, clarifying that the intended
next step was training. This supersedes the original staging-only interpretation
and authorizes launch of the reviewed baseline without another approval. No
production source, dataset, accepted plan or parameters changed. No additional
tests were necessary: the previously reviewed unchanged trainer and all 38
synthetic tests already cover launch, baseline and locking.

Main observed `not_started`, verified the GPU lock was free and GPU idle, then
called `ops.py start` once. Controller PID 3873/start ticks 44912542; actual
trainer launcher PID 3878/start ticks 44914808. Structured status is
running/training, PID/start identity verified alive, total 12 epochs. GPU memory
grew from 1 MiB to 7,422 MiB during model loading. No local watch/workflow/backup
was started; final/epoch weights stay remote. Completion is not yet claimed.

Subsequent GPU metadata confirms computation: 13,612 MiB used and 80% GPU
utilization. The detached training remains running; no checkpoint claimed yet.
