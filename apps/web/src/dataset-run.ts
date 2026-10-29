import type { CharacterRunRequest, DatasetItem } from './api'
import { compilePromptComments } from './prompt-weights'

export const MAX_DATASET_ITEMS = 300
export const MAX_DATASET_PROMPT_LENGTH = 1000
export const MAX_STYLE_POOL = 8
export const MAX_REFERENCES = 4
export const MAX_TRAITS_LENGTH = 1000
export const CUSTOM_CATEGORY = 'custom'

export interface DatasetEntry {
  id: string
  category: string
  prompt: string
  selected: boolean
}

export function nextCustomId(entries: readonly DatasetEntry[]): string {
  let index = 1
  while (entries.some(entry => entry.id === `custom-${index}`)) index += 1
  return `custom-${index}`
}

export function hasCommentLine(prompt: string): boolean {
  return prompt.split(/\r\n|\r|\n/).some(line => line.replace(/^[ \t]+/, '').startsWith('//'))
}

/**
 * Mirrors the server definition rules so invalid runs never reach the paid POST.
 * With a style pool, the longest effective style bounds every rotated combination;
 * character traits prefix every item.
 */
export function datasetItems(entries: readonly DatasetEntry[], styles: readonly string[], traits = ''): DatasetItem[] {
  const selected = entries.filter(entry => entry.selected)
  if (!selected.length) throw new Error('请至少选择一条训练集提示词。')
  if (selected.length > MAX_DATASET_ITEMS) throw new Error(`一次最多运行 ${MAX_DATASET_ITEMS} 条提示词。`)
  if (!styles.length || styles.length > MAX_STYLE_POOL) throw new Error(`画风池需要 1–${MAX_STYLE_POOL} 个画风。`)
  const effectiveStyles = styles.map(style => compilePromptComments(style).trim())
  if (effectiveStyles.some(style => !style)) throw new Error('训练集批跑需要填写画风；画风池中的每一项都不能为空。')
  if (styles.some(style => style.length > 3000)) throw new Error('单个画风不能超过 3000 字符。')
  const longest = Math.max(...effectiveStyles.map(style => style.length))
  const prefix = traits.trim() ? traits.trim().length + 2 : 0
  const ids = new Set<string>()
  return selected.map((entry, index) => {
    const label = `第 ${index + 1} 条提示词`
    if (!/^[a-z0-9][a-z0-9-]*$/.test(entry.id) || entry.id.length > 64 || ids.has(entry.id)) throw new Error(`${label}编号无效，请重置后重试。`)
    ids.add(entry.id)
    if (!entry.prompt.trim()) throw new Error(`${label}为空。`)
    if (entry.prompt.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${label}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
    if (hasCommentLine(entry.prompt)) throw new Error(`${label}不能包含以 // 开头的注释行。`)
    if (longest + 2 + prefix + entry.prompt.trim().length > 3000) throw new Error(`${label}与画风${prefix ? '、角色特征' : ''}合计超过 3000 字符。`)
    return { id: entry.id, prompt: entry.prompt }
  })
}

export interface CharacterSettings {
  traits: string
  mode: 'vibe' | 'img2img'
  referenceIds: string[]
  strength: string
  noise: string
}

function ratio(value: string, label: string, min: number, max: number): number {
  const number = Number(value)
  if (!value.trim() || !Number.isFinite(number) || number < min || number > max) throw new Error(`${label}须为 ${min}–${max}。`)
  return number
}

export function characterRequest(settings: CharacterSettings, model: string, vibeModels: readonly string[]): CharacterRunRequest {
  if (!settings.traits.trim()) throw new Error('请填写角色特征标签。')
  if (settings.traits.length > MAX_TRAITS_LENGTH) throw new Error(`角色特征不能超过 ${MAX_TRAITS_LENGTH} 字符。`)
  if (hasCommentLine(settings.traits)) throw new Error('角色特征不能包含以 // 开头的注释行。')
  if (!settings.referenceIds.length) throw new Error('请至少选择一张参考图。')
  if (settings.referenceIds.length > MAX_REFERENCES) throw new Error(`最多选择 ${MAX_REFERENCES} 张参考图。`)
  if (settings.mode === 'vibe') {
    if (!vibeModels.includes(model.trim())) throw new Error('Vibe Transfer 只支持 V4 / V4.5 模型，请在生成设置中切换模型或改用图生图。')
    return { traits: settings.traits, mode: 'vibe', reference_ids: [...settings.referenceIds] }
  }
  return {
    traits: settings.traits, mode: 'img2img', reference_ids: [...settings.referenceIds],
    strength: ratio(settings.strength, '图生图 strength', 0.01, 0.99),
    noise: ratio(settings.noise, '图生图 noise', 0, 0.99),
  }
}
