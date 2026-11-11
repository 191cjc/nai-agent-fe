# Additional fixed GPT inputs

Operator explicitly requests appending these two runs to the existing enabled
timer, after Siling/Zhengli/Bojiaqiu. Owner remains
`48fd7397-53cc-422a-8bac-69293871848c`; lane must be `gpt`.

| Name | Run ID | Role | Trigger | Priority |
| --- | --- | --- | --- | --- |
| gpt音织 | 5e49840f-5865-4c1c-9e03-247b1d3acd03 | yinzhi | aoqiyinzhi | 4 |
| gpt安 | 354f7cbc-4781-4b86-93d2-a300492fb932 | an | aoqian | 5 |

Both are currently running, 0/138 processed, 0 successes/failures at identity
inspection. Metadata came from owner-scoped `experiment_names` JOIN
`style_experiment_runs`; no private definition/prompt/caption/image content read.
Original Siling is uploading; Zhengli is completed with 129 successes/9 failures;
Bojiaqiu is still generating. Never stop the existing service or remote training.

Staging source-only root: `/home/ubuntu/lora-kit/aoqi_auto_1110_gpt_extend`.
Live root: `/home/ubuntu/lora-kit/aoqi_auto_1110_gpt` (root-owned/private).
Agents own only staging files; main alone deploys and observes production.
Keep all template bytes/hashes unchanged and preserve original SPECS prefix.
Regress exact five-run metadata selection plus restart with original accepted
state/snapshots; existing lock/readiness/predecessor/remote-only behavior persists.
Update release dispatcher hash; no app changes or new framework.
