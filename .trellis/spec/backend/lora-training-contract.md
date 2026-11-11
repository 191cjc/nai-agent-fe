# Private LoRA Training Operations

## Scope / Trigger

Use this contract when exporting this application's private datasets into an
external LoRA trainer, changing its queue, or overlapping remote uploads and
training. The reference implementation is
`/home/ubuntu/lora-kit/aoqi_training_1108/`; its reviewed source fingerprints and
runtime evidence live in the corresponding Trellis task's `research/` directory.
This is an external operational integration, not a public API or web feature.
The fixed appended-stage reference is
`/home/ubuntu/lora-kit/aoqi_training_1109_moyan2/`; its predecessor is the accepted
style/Longzhu operation in `/home/ubuntu/lora-kit/aoqi_training_1109_v3/`.

## Signatures

- `prepare.py --extend`: append newly pinned jobs only when the existing fixed
  plan is an exact prefix; preserve all original snapshots and manifests.
- `verify_prepared(root, check_hashes=True, expected_plan=None, check_datasets=True)`:
  use `check_datasets=False` for immutable metadata bootstrap only.
- `ops.py bootstrap`: upload source, plan/prepared/queue/incremental metadata and
  manifests before accepting a controller; do not wait for every remote dataset.
- `remote_train.py verify-job --root <root> --job <fixed-job-name>`: verify complete
  file pairs, sizes and hashes under that dataset's lock, then publish readiness.
- `ops.py start`, followed by `ops.py background`: start one detached controller
  and resume uploading unready active jobs while training proceeds.
- `ops.py status`: return structured operational metadata; no raw trainer output.
- Appended stage: `remote_train.py predecessor --root <tail-root>` returns
  `{state: waiting, code: <static-code>}`, `{state: succeeded, operation,
  plan_sha256}`, or `{state: blocked, code: <static-code>}`. Internal
  `predecessor_status()` / `require_predecessor()` use fixed predecessor metadata.
- Appended-stage `ops.py background`: upload/verify its dataset first, poll the
  predecessor protocol, then inspect own acceptance before starting/reattaching.
  `run --gpu-lock-fd <fd>` accepts only the launcher's inherited GPU lock FD.

## Contracts

- Operator authorization permits dedicated exporter/trainer programs to consume
  and transfer private data. Assistants inspect names, counts, sizes, timestamps,
  status and hashes only. Never inspect images, captions, database prompt text,
  private logs or model metadata headers. Redirect program diagnostics privately.
- `plan.json` fixes source runs, job order and training identity; `prepared.json`
  pins its SHA-256 and every manifest. Export honors owner-scoped caption
  overrides, discards and pending/completed purges, without changing source data.
- Opt-in `incremental.json` is exactly
  `{version: 1, operation: <fixed-operation>, plan_sha256: <plan-sha256>}`.
  Without it, the complete-transfer mode remains available.
- `queue.json` pins version/operation/plan hash and ordered `active_jobs` plus
  `deferred_jobs`. Deferred style has state `deferred`, no success/artifacts, and
  does not contribute to the active final-backup completion count.
- Bootstrap holds the controller guard and staging barrier; accepted controller
  state prevents source/plan/manifest replacement. Subsequent transfers contain
  only one unready active dataset's PNG/caption filenames.
- `jobs/<name>/ready.json` pins version, operation, job, plan hash and manifest
  hash, plus `verified_at`. A manifest or partial transfer alone is not readiness.
- The rsync receiver and readiness publisher share `.dataset.lock`. Restrict the
  receiver destination to the exact selected dataset subset and pass its lock FD
  into rsync. A ready marker prevents all further uploader writes to that set.
- The controller initially validates immutable metadata, then waits in
  `waiting_data` only for its next active job. Recheck that job's actual hashes
  before training. Later incomplete datasets must not block an earlier ready job.
- Keep one GPU trainer, inherited controller/GPU locks, actual subprocess exits,
  fresh final/epoch artifacts and checksums. Advance only after validated success;
  failed or uncertain accepted stages never automatically retrain.
- Local workflows reconnect after transport errors, consult remote acceptance
  before submitting, skip ready data on resume and back up verified final weights.
- Appending to a live immutable queue uses a separate fixed operation/root and
  snapshot; never replace accepted source/plan/queue to append jobs. Pin the
  predecessor root, operation, plan hash, prepared identity, ordered active jobs,
  triggers and exact final filenames. An idle GPU or a vanished process is not
  predecessor success.
- The fixed predecessor gate requires completed state, every stage succeeded
  with recorded exit code 0, and revalidated sizes/hashes for all recorded
  nonempty epoch/final weights. The final weight can represent epoch 12; do not
  require a separate `-000012` checkpoint when the trainer saves only the final.
  Running/launching predecessors must retain their PID/start-time identity;
  failed, missing, changed or uncertain predecessors block the tail.
- Upload and predecessor polling never hold the shared GPU lock. Tail launch
  acquires the predecessor's GPU exclusion lock before acceptance and passes it
  through the detached controller into its trainer; controller and trainer
  creation independently recheck the predecessor. The fixed 1109 lock is
  `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`. Retain operation and GPU locks in
  surviving trainer children. Only final weights enter local result backups.

## Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Incremental config differs from pinned identity | `incremental_config_mismatch` |
| Unknown/reordered/omitted queue job | Reject; never silently change work |
| Next dataset lacks readiness | `waiting_data`; later uploads continue |
| Missing/corrupt file during verification | No ready marker or trainer launch |
| Ready marker pins different metadata | `dataset_readiness_identity_mismatch` |
| Receiver targets root/another dataset | `dataset_receiver_arguments_invalid` |
| Upload targets ready data | `ready_dataset_is_immutable` |
| Receiver parent exits while rsync survives | Child retains lock until exit |
| Trainer exits nonzero or final artifact is stale/missing | Fail; no next trainer |
| All active jobs succeed and final backups verify | Complete active queue only |
| Predecessor is alive and still training | `waiting` / `predecessor_in_progress`; poll without a GPU lock |
| Predecessor plan hash changed | `blocked` / `predecessor_plan_hash_mismatch` |
| Predecessor failed | `blocked` / `predecessor_failed`; local workflow stops with `predecessor_not_successful` |
| Running predecessor controller vanished | `blocked` / `predecessor_controller_missing_uncertain` |
| Predecessor final is missing or artifact hash changed | Block with `completed_final_missing` / `completed_checkpoint_changed` |
| Shared GPU lock remains held | No accepted overlapping trainer (`operation_locked`) |

## Good / Base / Bad Cases

- Good: verify existing Xingjiang/Nuoya/Zhengli snapshots, start Xingjiang, and
  upload later characters concurrently; retain checkpoint/readiness timestamps
  demonstrating actual overlap.
- Good: upload Moyan2 in a new root while Longzhu trains, wait for verified
  style/Longzhu success, then acquire their shared GPU lock and train Moyan2.
- Base: absent incremental config preserves the original complete-transfer flow.
- Bad: wait for all remote datasets despite a ready first character, mark a
  manifest as ready without checking files, or rewrite ready data/controller code.

## Tests Required

Use disposable synthetic SQLite/image fixtures and fake trainers. Run the three
operation modules with unittest, targeted Ruff E/F/I/UP/B (Python 3.12, 100-column
limit), and compilation. No Python type checker is configured.

Assert first training starts while later data is absent; next training waits;
partial/corrupt data never starts; actual rsync cannot write ready/other datasets;
orphan receiver/trainer children retain locks; resume never duplicates acceptance;
fixed order, deferral, failure stops and active-only verified backups survive.
Extension tests must prove original snapshot bytes stay unchanged and only new
source runs are read. Fake tests do not establish production overlap or completion.
For a fixed tail, additionally assert upload precedes prerequisite waiting;
pending, failed, corrupt and mismatched predecessors cannot submit a trainer;
remote gates reject direct bypass; inherited shared locks survive orphan children;
and a lost launch reply reattaches rather than launching twice. Verify one exact
final-only backup for the tail separately from the predecessor's backup count.

## Wrong vs Correct

- Wrong: use one all-datasets upload barrier to gate an already verified role, or
  remove status/locks to bypass uncertain training.
- Correct: bootstrap immutable metadata once, publish readiness after locked file
  verification, train the next ready role while uploading later roles, and
  preserve accepted state plus process/start-time identities across reconnects.

## Scenario: Scheduled completion-to-training pipeline

### 1. Scope / Trigger

Use `/home/ubuntu/lora-kit/aoqi_auto_1110_gpt` for the operator-authorized fixed
five-run GPT completion/export/upload/train automation (Siling, Zhengli,
Bojiaqiu, Yinzhi and An). This integration is
outside the application; do not broaden selection to other active runs. The
operator's remote-only weight policy supersedes the earlier backup examples.

### 2. Signatures

- `dispatch.py tick`: one singleton scheduled pass; consumes only read-only run
  status/count metadata and invokes dedicated per-root exporter/transfer/trainer
  subprocesses. `dispatch.py status`: emits saved structured metadata only.
- Generated `ops.py` actions are exactly `bootstrap`, `upload`, `status`, `start`,
  `predecessor`, and `verify-completion`. There is no backup argument/action or
  background watcher. `remote_train.py verify-completion` revalidates successful
  exits and all recorded artifact sizes/SHA-256 without reading model headers.
- `aoqi-auto-1110-gpt.service` is a root oneshot with `UMask=0077`; its timer runs
  after boot and 60 seconds after service inactivity, preventing overlapping
  long uploads. A local file lock also excludes concurrent manual ticks.

### 3. Contracts

- Pin owner, GPT lane and the five approved run IDs/triggers in code. Only
  `completed` source runs may export retained successes. Failed generation groups
  are excluded, never regenerated; overrides/discards/purges remain authoritative.
- Freeze each independent operation's completed-source count, source hashes and
  snapshot identity once. Preserve the reviewed exporter unchanged. Never rewrite
  initialized or remotely accepted operation sources, plans or ready datasets.
- Every generated fixed plan pins the full completed Huangjin prerequisite and
  literal `/hy-tmp/.aoqi_training_1109_v3.gpu.lock`. Each character uses the same
  independent NoobAI training baseline. Acquire/inherit operation and GPU locks
  before acceptance, and revalidate the prerequisite in the controller.
- Reconcile all known remote acceptances before actions. SSH failure cannot mean
  absent acceptance. Observe live accepted work; never automatically retrain a
  failed or uncertain accepted stage. Remote completion needs exit 0 and actual
  artifact hash verification before the next launch.
- Bootstrap metadata and use the inherited dataset-lock/readiness receiver.
  Upload completed sources independently of GPU activity and pending sources.
  Launch an existing ready dataset first, or immediately after its upload, before
  beginning another long upload. Keep at most one accepted live trainer.
- Service diagnostics remain private. Status contains only IDs, counts, static
  codes, process identity, status, filenames, sizes and hashes. No image/caption/
  prompt content, private logs or model headers enter assistant-visible output.
- Root service probes and upload/start transports explicitly use
  `UserKnownHostsFile=/home/ubuntu/.ssh/known_hosts` and
  `StrictHostKeyChecking=yes`, with the fixed identity file, `BatchMode=yes` and
  `IdentitiesOnly=yes`. Verify connectivity as the actual service user before
  activation; root's default host-trust store can differ from the operator's.
- All epoch/final weights stay remote; never invoke older backup/watch/workflow
  commands. Timer restarts must preserve acceptance and snapshot state.
- Adding explicitly authorized sources appends fixed dispatcher entries while
  preserving the original prefix, template bytes and generated operation
  fingerprints. Check a source-only staging copy first. Pause only the local
  timer during dispatcher/release replacement, keep active uploads and remote
  processes running, then restore the enabled timer. The current pass keeps its
  loaded scope; the next pass includes the new entries. Never rewrite runtime
  acceptance or frozen source snapshots to extend selection.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Source running/queued | Wait; no exporter or regeneration |
| Owner/lane/run mismatch or zero successes | Block that source; no trainer |
| Changed frozen template/source/snapshot | Fail closed; preserve accepted state |
| Operator appends Yinzhi/An | Preserve original three identities and snapshots; select exactly five fixed IDs |
| Partial ambiguous export | `partial_export_requires_review`; do not overwrite |
| Remote probe unavailable | Retry observation; never infer no acceptance |
| Root service cannot verify the SSH host | Use the existing explicit trust file; never disable host verification |
| Authoritative absence after unaccepted probe uncertainty | Resume retryable work; retain real integrity blocks |
| Accepted state disappears or controller identity dies | Block further launches |
| GPU lock busy before acceptance | Wait without creating another accepted stage |
| Launch reply lost | Reconcile remote acceptance before any further submission |
| Accepted trainer fails or completed artifact changes | Stop further launches; never auto-retrain |

### 5. Good / Base / Bad Cases

- Good: the Siling source finishes, uploads and trains while the other two GPT
  sources still generate; their later uploads can overlap that detached trainer.
- Base: a timer rerun observes the existing accepted controller and skips its
  immutable ready dataset. All model files remain on the GPU server.
- Bad: treat an SSH timeout as not-started, wait for all uploads before launching
  the first ready set, or reuse an older upload function that downloads finals.

### 6. Tests Required

Use synthetic SQLite/images and fake transports/trainers. Assert exact selection,
completed-only export, independent uploads and first-upload/start/next-upload
ordering; frozen source/snapshot preservation; readiness locks and corrupt-pair
refusal; atomic/inherited GPU exclusion; predecessor/finished-artifact corruption;
lost-reply reattachment, retryable absence recovery and accepted failure stops;
explicit trusted-host SSH options and no reachable model download. Run full
new-operation unittest modules, Ruff
E/F/I/UP/B (py312, 100 columns) and compilation. Verify actual unit activation and
first-poll states separately; synthetic checks do not establish deployment.
For selection extensions, prove that existing accepted state and generated
source/plan/prepared identities survive the append; incomplete added sources
must not delay a ready or running original role. Existing source fingerprints
must remain identical during production promotion.

### 7. Wrong vs Correct

- Wrong: call an existing background workflow after the user prohibited backup,
  or launch multiple roots and let their child controllers contend after acceptance.
- Correct: use the new no-backup fixed dispatcher, reconcile accepted work and
  atomically acquire the existing GPU lock before accepting one ready trainer.
- Wrong: rewrite a live accepted queue, or wait for its completion while holding
  the GPU lock it needs.
- Correct: prepare/upload the fixed tail independently, verify predecessor
  success without that lock, and inherit the shared lock only across tail launch
  and training.
