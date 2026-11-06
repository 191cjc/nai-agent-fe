# Pause run claims while the provider is unreachable

## Problem
2026-11-06 01:47–02:51: the NovelAI MCP host stopped accepting connections. The scheduler
kept claiming one group every ~6 s (5 s connect timeout + 1 s tick); each failed as
`provider_unavailable`, so ~400 queued dataset items across 6 runs were burned as failures
within an hour. MCP failures were not logged, so the cause had to be inferred from DB timings.

## Requirements
- A pre-payment transient failure (`provider_unavailable`, `provider_rate_limited`) on a lane
  opens a lane cooldown (15 s doubling to 10 min). While cooling down, the scheduler claims no
  new group on that lane; waiting runs consume no ordinal (same as queue contention).
- When the cooldown elapses, the NovelAI lane runs an unpaid MCP `initialize` probe; success
  resumes claims, failure extends the backoff. Lanes without a probe (GPT) resume claims.
- Any successful group on the lane clears the state.
- The failed group itself stays failed — no auto retry (durable-experiment contract).
- Ordinary single generations are not gated (users get an immediate error).
- `RunState.provider_paused_until` (additive, epoch seconds | null) for running runs on a
  paused lane; web run status shows 「上游暂不可用 · 等待恢复」.
- Log lane pause/resume and NovelAI failure codes (no prompts, tokens or upstream bodies).
