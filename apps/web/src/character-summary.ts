import type { CharacterRunPlan } from './api'

export function characterSnapshotSummary(plan: CharacterRunPlan): string {
  const mode = plan.mode === 'vibe' ? 'Vibe Transfer' : `图生图（strength ${plan.strength} · noise ${plan.noise}）`
  return `角色特征：${plan.traits} · ${mode} · 参考图 ${plan.references.length} 张`
}
