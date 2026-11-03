import type { CharacterRunPlan, PreciseType } from './api'

export function preciseLabel(type: PreciseType | null | undefined): string {
  return type === 'style' ? '画风' : type === 'character&style' ? '角色 + 画风' : '角色'
}

export function characterSnapshotSummary(plan: CharacterRunPlan): string {
  const mode = plan.mode === 'gpt' ? `GPT 参考图生成（质量 ${plan.gpt_quality ?? '自动'}）` : plan.mode === 'vibe' ? `Vibe Transfer（信息提取度 ${plan.information_extracted ?? 1} · 强度 ${plan.reference_strength ?? 1}）` : plan.mode === 'precise' ? `精准参考（${preciseLabel(plan.precise_type)} · 强度 ${plan.precise_strength ?? 1} · 保真度 ${plan.precise_fidelity ?? 1}）` : `图生图（strength ${plan.strength} · noise ${plan.noise}）`
  return `角色特征：${plan.traits} · ${mode} · 参考图 ${plan.references.length} 张`
}
