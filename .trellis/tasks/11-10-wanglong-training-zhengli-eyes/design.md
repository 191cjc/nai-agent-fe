# Design

Reuse reviewed source from `/home/ubuntu/lora-kit/aoqi_training_1109_v3` into new
isolated `/home/ubuntu/lora-kit/aoqi_training_1110_wanglong`. Adapt only fixed
job/operation metadata, default paths and operation-specific synthetic tests.
Remote root `/hy-tmp/aoqi_training_1110_wanglong`. The operator superseded the
initial backup plan: all weights stay remote; no local backup is authorized.

Sole job `char_wanglong_gpt_1110`: character, repeats 3, trigger `aoqiwanglong`,
run `2bfd3586-5c15-49ab-abe9-91fa52caa083`, expected images 134. Keep the quality
prefix, private exporter and approved baseline. Pair-mixing seed 20261110;
trainer seed 42.

Use existing shared GPU exclusion `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`,
retained by controller and surviving trainer children. Existing operations are
completed; no predecessor gate or accepted queue edits are needed.

Main owns task records, SSH, production preparation and transfer/start.
Implement/check agents own only new operation source and synthetic checks, never
production content or GPU operations. Preparation uses the application's venv
and privileged private exporter. Verify count/hash metadata, bootstrap immutable
source/manifests, transfer/verify the sole dataset and launch once. The remote
controller/trainer are detached and independent of local monitoring. The initial
local monitor/backup workflow was stopped after the operator cancelled backup.
Use `ops.py status` for metadata-only checks; do not run backup/watch/workflow/
background, which retain automatic local backup behavior in frozen source.
Raw diagnostics remain private; never inspect them.

The operator cancelled Zhengli diagnosis after approval. Continue only Wanglong
training; no extra investigation or model loading.

Before acceptance, rollback affects only unaccepted new operation files. After
acceptance preserve source/state and never auto-retry uncertain training.

## Huangjin staging extension

Prepare an independent, unaccepted source-only clone at
`/home/ubuntu/lora-kit/aoqi_training_1110_huangjin`; remote root
`/hy-tmp/aoqi_training_1110_huangjin`. Use job `char_huangjin_gpt_1110`, trigger
`aoqihuangjin`, sole source `d97531fa-5be1-4eba-9081-2e424b5e6bce` and expected
123 pairs. Preserve the reviewed private exporter and trainer protocols; only
fixed identity/path values and corresponding synthetic assertions change.
Use complete-transfer `ops.py stage`, which does not call backup or launch.
Do not invoke `upload`, `backup`, `start`, `watch`, `workflow` or `background`.
No accepted operation, data or application code is changed. Main verifies
Wanglong successful exit and remote final/checksums before Huangjin transfer.
Main alone handles production preparation/staging; agents inspect source and
synthetic fixtures only. Keep local backup disabled throughout.

## Huangjin training clarification

The latest operator message supersedes the initial staging-only interpretation:
start Huangjin now using the already reviewed, unchanged trainer and baseline.
Run `ops.py start` once after inspecting acceptance and GPU exclusion metadata;
the detached remote controller handles execution and checksums. Observe with
`status` only. Never launch backup/watch/workflow/background. No accepted source,
dataset, snapshot or training parameters need modification. Trigger/final stem
remains `aoqihuangjin`; main owns launch and runtime checks.

## Durable automatic three-run pipeline

Smallest missing behavior: source completion currently needs a human to export,
upload and launch. Implement a fixed three-run dispatcher outside the application
under `/home/ubuntu/lora-kit/aoqi_auto_1110_gpt`. No accepted Wanglong/Huangjin
source, dataset, plan or queue is edited. Use source-only private exporter/trainer
templates derived from the reviewed operations, with a root systemd oneshot
service invoked by a 60-second timer. Main installs/enables it after independent
review; source/tests/units belong to implement/check agents. Program diagnostics
are private; assistants read structured status only.

The dispatcher selects exactly the pinned owner, GPT lane and three run IDs in
`research/auto-queue-inputs.md`. It reads status/count metadata from read-only
SQLite. When each run is completed, freeze an independent one-job source-only
operation from pinned templates and completed source count metadata, then call
the unchanged private exporter, immutable metadata bootstrap and the existing
dataset-lock/readiness upload protocol. Honor actual marks
and fail on missing source files/zero usable images; never regenerate failures.
Each export/upload can proceed without the other sources being completed.
Never rewrite an initialized or remotely accepted operation. Each generated root
runs in an isolated subprocess to avoid cross-job module cache contamination.

Use the reviewed Moyan2 dependent launcher/controller inheritance implementation
for atomic GPU acquisition before acceptance and inherited GPU/operation locks.
All three independent character operations pin completed Huangjin as the guard
predecessor. The pinned predecessor root/operation/plan hash/ordered jobs/final
identity and literal shared GPU lock path must be included in each fixed plan.
Do not derive that lock path from the predecessor name: it remains
`/hy-tmp/.aoqi_training_1109_v3.gpu.lock`. This is execution gating; every
character trains independently from the same NoobAI base, with the existing
Wanglong/Huangjin baseline. Revalidate predecessor successful exit and artifact
sizes/SHA-256 before launch and independently at controller creation.

Every tick takes a local singleton lock, reconciles all three known remote
acceptances before staging/launch decisions, and permits at most one active
trainer. Ready datasets are chosen in pinned priority, skipping incomplete
generation. An already accepted trainer is observed rather than resubmitted.
Failed/uncertain accepted stages block further launches; transport failures
remain retryable observations and are never interpreted as absent acceptance.
A completed training stage must have all remote artifact sizes/hashes revalidated
before the dispatcher accepts success and permits the next launch. Upload and
polling never hold the GPU lock. Losing an SSH start reply must reconcile accepted
remote state before any retry. Template/source and frozen snapshot identity
checks must make restarts safe after partial export/upload or process crashes.

The scheduler and new operation CLI must never download/back up model weights.
Do not invoke inherited watch/workflow/backup. The new unaccepted ops template
must remove backup calls from upload and omit model-backup actions/arguments;
expose only the needed commands. Retain inherited receiver dataset locks and
immutable readiness, including surviving rsync child exclusion. Persist
metadata-only per-job state and offer a status
CLI. Service stdout/stderr goes to private logs, with UMask 0077. A root oneshot
service is needed for the private read-only DB/exporter; the timer runs again
after service inactivity and starts after boot. It must not overlap itself or
require a live Codex session. Only main performs production DB/SSH/deployment.

Validate fixed selection/completion gating, interrupted preparation/staging,
independent uploads, GPU exclusion including inherited lock survival, uncertain
acceptance/transport recovery, no duplicate or failed-training retry, corrupt
predecessor/artifacts, restart identity checks and absence of local backups using
synthetic SQLite/data and fake transports/trainers. Record actual timer health
and first-poll metadata separately from synthetic test results.

## Five-run extension

Append Yinzhi and An to the fixed dispatcher `SPECS` with their newly authorized
IDs/triggers. Preserve the original three entries and all template hashes,
predecessor/base/training constants, generated operations, source snapshots,
remote state and current upload/controller/trainer processes. Only dispatcher,
release pin, corresponding synthetic assertions, README and descriptive unit
text may need updates. This is a constant-set extension, not a new queue engine.

Work in a source-only staging copy
`/home/ubuntu/lora-kit/aoqi_auto_1110_gpt_extend`; agents never edit the running
root or inspect production data. Main promotes the independently checked files
into `/home/ubuntu/lora-kit/aoqi_auto_1110_gpt`. Temporarily stop only the timer
while replacing dispatcher/release together, leave any active oneshot and its
remote children running, then re-enable the same timer. A currently executing
pass retains its original in-memory scope; the next pass loads all five IDs.
No existing generated operation source/plan/template may change. Verify the
original immutable metadata fingerprints before and after promotion and record
timer health plus the actual first five-run poll separately.
