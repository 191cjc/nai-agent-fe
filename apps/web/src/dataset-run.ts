import type { CharacterPrompt, CharacterRunRequest, DatasetItem, PreciseType } from './api'
import { compilePromptComments } from './prompt-weights'

export const MAX_DATASET_ITEMS = 300
export const MAX_DATASET_PROMPT_LENGTH = 1000
export const MAX_STYLE_POOL = 8
export const MAX_REFERENCES = 4
export const MAX_TRAITS_LENGTH = 1000
export const CUSTOM_CATEGORY = 'custom'
export const MAX_ITEM_CHARACTERS = 6

export interface DatasetEntry {
  id: string
  category: string
  /** Shared scene; multi-person entries describe each person in `characters`. */
  prompt: string
  /** One native character prompt per person, left to right. */
  characters?: readonly string[]
  selected: boolean
}

/** People spread evenly left to right at mid height (NovelAI's 0.1–0.9 grid). */
function characterPositions(prompts: readonly string[]): CharacterPrompt[] {
  return prompts.map((prompt, index) => ({
    prompt, x: Math.round((0.1 + 0.8 * (index + 1) / (prompts.length + 1)) * 100) / 100, y: 0.5,
  }))
}

/** One-line view of a frozen item: the scene, then each person in order. */
export function datasetItemText(item: DatasetItem): string {
  return [item.prompt, ...(item.characters ?? []).map((character, index) => `人物 ${index + 1}：${character.prompt}`)].join(' ｜ ')
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
export function datasetItems(entries: readonly DatasetEntry[], styles: readonly string[], traits = '', nativeCharacters = true): DatasetItem[] {
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
    const characters = entry.characters ?? []
    if (!characters.length) return { id: entry.id, prompt: entry.prompt }
    if (traits.trim()) throw new Error(`${label}是多人条目，角色训练集不支持，请取消选择。`)
    if (!nativeCharacters) throw new Error(`${label}是多人条目，需要支持多角色提示词的 V4 / V4.5 / V5 模型；请切换模型或取消「多人互动」。`)
    if (characters.length > MAX_ITEM_CHARACTERS) throw new Error(`${label}最多 ${MAX_ITEM_CHARACTERS} 个人物。`)
    characters.forEach((character, person) => {
      const name = `${label}的人物 ${person + 1}`
      if (!character.trim()) throw new Error(`${name}为空。`)
      if (character.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${name}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
      if (hasCommentLine(character)) throw new Error(`${name}不能包含以 // 开头的注释行。`)
    })
    return { id: entry.id, prompt: entry.prompt, characters: characterPositions(characters) }
  })
}

export type GptSize = 'portrait' | 'square' | 'landscape'
export const GPT_SIZES: Record<GptSize, { label: string; width: number; height: number }> = {
  portrait: { label: '竖版 1024×1536', width: 1024, height: 1536 },
  square: { label: '方形 1024×1024', width: 1024, height: 1024 },
  landscape: { label: '横版 1536×1024', width: 1536, height: 1024 },
}

export interface CharacterSettings {
  traits: string
  mode: 'vibe' | 'img2img' | 'gpt' | 'precise'
  referenceIds: string[]
  strength: string
  noise: string
  /** Vibe only: encode_vibe information_extracted, 0.01–1. */
  information: string
  /** Vibe only: generation-time influence of the vibes, 0.01–1. */
  vibeStrength: string
  /** GPT only: output size, quality (auto = model default) and images per item. */
  gptSize: GptSize
  gptQuality: 'auto' | 'low' | 'medium' | 'high'
  gptSamples: string
  /** Precise Reference only: what to copy, strength 0.01–1 and fidelity 0–1. */
  preciseType: PreciseType
  preciseStrength: string
  preciseFidelity: string
}

function ratio(value: string, label: string, min: number, max: number): number {
  const number = Number(value)
  if (!value.trim() || !Number.isFinite(number) || number < min || number > max) throw new Error(`${label}须为 ${min}–${max}。`)
  return number
}

export function characterRequest(settings: CharacterSettings, model: string, vibeModels: readonly string[], preciseModels: readonly string[] = []): CharacterRunRequest {
  if (!settings.traits.trim()) throw new Error('请填写角色特征标签。')
  if (settings.traits.length > MAX_TRAITS_LENGTH) throw new Error(`角色特征不能超过 ${MAX_TRAITS_LENGTH} 字符。`)
  if (hasCommentLine(settings.traits)) throw new Error('角色特征不能包含以 // 开头的注释行。')
  if (!settings.referenceIds.length) throw new Error('请至少选择一张参考图。')
  if (settings.referenceIds.length > MAX_REFERENCES) throw new Error(`最多选择 ${MAX_REFERENCES} 张参考图。`)
  if (settings.mode === 'gpt') {
    return {
      traits: settings.traits, mode: 'gpt', reference_ids: [...settings.referenceIds],
      ...(settings.gptQuality === 'auto' ? {} : { gpt_quality: settings.gptQuality }),
    }
  }
  if (settings.mode === 'precise') {
    if (!preciseModels.includes(model.trim())) throw new Error('精准参考（Precise Reference）只支持 V4.5 模型，请在生成设置中切换模型。')
    return {
      traits: settings.traits, mode: 'precise', reference_ids: [...settings.referenceIds],
      precise_type: settings.preciseType,
      precise_strength: ratio(settings.preciseStrength, '精准参考强度', 0.01, 1),
      precise_fidelity: ratio(settings.preciseFidelity, '精准参考保真度', 0, 1),
    }
  }
  if (settings.mode === 'vibe') {
    if (!vibeModels.includes(model.trim())) throw new Error('Vibe Transfer 只支持 V4 / V4.5 模型，请在生成设置中切换模型或改用图生图。')
    return {
      traits: settings.traits, mode: 'vibe', reference_ids: [...settings.referenceIds],
      information_extracted: ratio(settings.information, '信息提取度', 0.01, 1),
      reference_strength: ratio(settings.vibeStrength, 'Vibe 强度', 0.01, 1),
    }
  }
  return {
    traits: settings.traits, mode: 'img2img', reference_ids: [...settings.referenceIds],
    strength: ratio(settings.strength, '图生图 strength', 0.01, 0.99),
    noise: ratio(settings.noise, '图生图 noise', 0, 0.99),
  }
}
