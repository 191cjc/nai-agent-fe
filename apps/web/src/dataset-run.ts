import type { CharacterPrompt, CharacterRunRequest, DatasetItem, PreciseType } from './api'
import { previewStyle, validateStyleEdits, type DatasetDraw, type StyleEdits } from './recipe'
import type { CharacterMode } from './character-prompts'
import { compilePromptComments } from './prompt-weights'

export const MAX_DATASET_ITEMS = 4000
export const MAX_DATASET_PROMPT_LENGTH = 1000
export const MAX_STYLE_POOL = 12
export const MAX_REFERENCES = 4
export const MAX_TRAITS_LENGTH = 1000
export const CUSTOM_CATEGORY = 'custom'
export const MAX_ITEM_CHARACTERS = 6

export interface DatasetCategory {
  id: string
  label: string
  description: string
}

export interface DatasetPrompt {
  id: string
  category: string
  prompt: string
  /** Multi-person items only: one native character prompt per person, left to right. */
  characters?: readonly string[]
}

/** Style entries generated from a random recipe. */
export const RECIPE_CATEGORY = 'recipe'

export interface DatasetEntry {
  id: string
  category: string
  /** Shared scene; multi-person entries describe each person in `characters`. */
  prompt: string
  /** One native character prompt per person, left to right. */
  characters?: readonly string[]
  selected: boolean
  /** Random-recipe entries: frozen draws, per-item style edits and source recipe. */
  draws?: readonly DatasetDraw[]
  styleEdits?: StyleEdits
  recipe?: { id: string; name: string }
  /** Recipe canvas hint; wins over the tag heuristic when automatic shapes are on. */
  shape?: ItemShape | null
}

/** Marks a recipe entry whose prompt was hand-edited (its draws may no longer match). */
export const EDITED_DRAW: DatasetDraw = { partition: '-meta', option: 'edited', label: '提示词已手动修改' }

export function markEdited(entry: DatasetEntry, prompt: string): DatasetEntry {
  if (!entry.draws?.length || entry.draws.some(draw => draw.partition === '-meta' && draw.option === 'edited')) return { ...entry, prompt }
  return { ...entry, prompt, draws: [...entry.draws, EDITED_DRAW] }
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

/** Comma-separated tags with empty entries and stray separators removed. */
export function tidyPrompt(prompt: string): string {
  return prompt.split(/[,，\n]/).map(tag => tag.replace(/\s+/g, ' ').trim()).filter(Boolean).join(', ')
}

export function hasCommentLine(prompt: string): boolean {
  return prompt.split(/\r\n|\r|\n/).some(line => line.replace(/^[ \t]+/, '').startsWith('//'))
}

/**
 * Mirrors the server definition rules so invalid runs never reach the paid POST.
 * Every pool style is checked after per-item edits; character traits prefix every item.
 */
export type ItemShape = 'portrait' | 'square' | 'landscape'
export interface ItemSize { width: number; height: number }

/** NovelAI canvases of about one megapixel per shape (same Anlas tier as 1024×1024). */
export const NAI_SHAPE_SIZES: Record<ItemShape, ItemSize> = {
  portrait: { width: 832, height: 1216 },
  square: { width: 1024, height: 1024 },
  landscape: { width: 1216, height: 832 },
}

export const SHAPE_LABELS: Record<ItemShape, string> = { portrait: '竖图', square: '方图', landscape: '横图' }

/**
 * Canvas shape from framing and pose tags: horizontal floor poses, wide shots,
 * scenery and full-body groups take landscape priority over full-body portrait.
 * Everything else is square.
 */
export function itemShape(prompt: string, characters: readonly string[] = []): ItemShape {
  const tags = new Set([prompt, ...characters].join(',').split(',').map(tag => tag.trim().toLowerCase()).filter(Boolean))
  const group = ['2girls', '3girls', '2boys', 'multiple girls'].some(tag => tags.has(tag)) || characters.length > 1
  const lying = ['lying', 'reclining', 'on back', 'on side', 'on stomach'].some(tag => tags.has(tag))
  const horizontal = ['all fours', 'crawling', 'plank', 'side plank', 'downward dog', 'seated forward fold'].some(tag => tags.has(tag))
  if (lying || horizontal || tags.has('wide shot') || tags.has('scenery') || (group && tags.has('full body'))) return 'landscape'
  if (tags.has('full body') || tags.has('cowboy shot')) return 'portrait'
  return 'square'
}

export function datasetItems(entries: readonly DatasetEntry[], styles: readonly string[], traits = '', nativeCharacters = true, sizes?: Record<ItemShape, ItemSize>): DatasetItem[] {
  const selected = entries.filter(entry => entry.selected)
  if (!selected.length) throw new Error('请至少选择一条训练集提示词。')
  if (selected.length > MAX_DATASET_ITEMS) throw new Error(`一次最多运行 ${MAX_DATASET_ITEMS} 条提示词。`)
  if (!styles.length || styles.length > MAX_STYLE_POOL) throw new Error(`画风池需要 1–${MAX_STYLE_POOL} 个画风。`)
  const effectiveStyles = styles.map(style => compilePromptComments(style).trim())
  if (effectiveStyles.some(style => !style)) throw new Error('训练集批跑需要填写画风；画风池中的每一项都不能为空。')
  if (styles.some(style => style.length > 3000)) throw new Error('单个画风不能超过 3000 字符。')
  const prefix = traits.trim() ? traits.trim().length + 2 : 0
  const ids = new Set<string>()
  return selected.map((entry, index) => {
    const label = `第 ${index + 1} 条提示词`
    if (!/^[a-z0-9][a-z0-9-]*$/.test(entry.id) || entry.id.length > 64 || ids.has(entry.id)) throw new Error(`${label}编号无效，请重置后重试。`)
    ids.add(entry.id)
    if (!entry.prompt.trim()) throw new Error(`${label}为空。`)
    if (entry.prompt.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${label}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
    if (hasCommentLine(entry.prompt)) throw new Error(`${label}不能包含以 // 开头的注释行。`)
    const characters = entry.characters ?? []
    const styleEdits = entry.styleEdits ? validateStyleEdits(entry.styleEdits, label) : undefined
    if (styleEdits && (styleEdits.add.length || styleEdits.remove.length)) {
      if (traits.trim()) throw new Error(`${label}带有画风增删，只能用于画风训练集。`)
      if (characters.length) throw new Error(`${label}带有画风增删，只能用于单人条目。`)
    }
    // Optional per-item canvas; absent keeps the run size (and the stored item unchanged).
    const size = sizes ? sizes[entry.shape ?? itemShape(entry.prompt, characters)] : null
    const canvas = size ? { width: size.width, height: size.height } : {}
    const recipe = {
      ...(entry.draws?.length ? { draws: [...entry.draws] } : {}),
      ...(styleEdits && (styleEdits.add.length || styleEdits.remove.length) ? { style_edits: styleEdits } : {}),
      ...(entry.recipe ? { recipe: entry.recipe } : {}),
    }
    // Recipe items: tidy separators left by hand edits ("a,, b ," -> "a, b") before sending.
    const prompt = recipe.draws ? tidyPrompt(entry.prompt) : entry.prompt
    for (const style of styles) {
      const resolved = recipe.style_edits ? previewStyle(style, recipe.style_edits) : style
      const effective = compilePromptComments(resolved).trim()
      if (!effective) throw new Error(`${label}的画风增删会让画风变空。`)
      if (resolved.length > 3000) throw new Error(`${label}增删后的画风超过 3000 字符。`)
      if (effective.length + 2 + prefix + prompt.trim().length > 3000) throw new Error(`${label}与增删后的画风${prefix ? '、角色特征' : ''}合计超过 3000 字符。`)
    }
    if (!characters.length) return { id: entry.id, prompt, ...canvas, ...recipe }
    if (traits.trim()) throw new Error(`${label}是多人条目，角色训练集不支持，请取消选择。`)
    if (!nativeCharacters) throw new Error(`${label}是多人条目，需要支持多角色提示词的 V4 / V4.5 / V5 模型；请切换模型或取消「多人互动」。`)
    if (characters.length > MAX_ITEM_CHARACTERS) throw new Error(`${label}最多 ${MAX_ITEM_CHARACTERS} 个人物。`)
    characters.forEach((character, person) => {
      const name = `${label}的人物 ${person + 1}`
      if (!character.trim()) throw new Error(`${name}为空。`)
      if (character.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${name}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
      if (hasCommentLine(character)) throw new Error(`${name}不能包含以 // 开头的注释行。`)
    })
    return { id: entry.id, prompt: entry.prompt, characters: characterPositions(characters), ...canvas }
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
  mode: CharacterMode
  referenceIds: string[]
  /** GPT only: output size, quality (auto = model default) and images per item. */
  gptSize: GptSize
  gptQuality: 'auto' | 'low' | 'medium' | 'high'
  gptSamples: string
  /** GPT only: items generated at once, 1..server maximum. */
  gptConcurrency: string
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

export function characterRequest(settings: CharacterSettings, model: string, preciseModels: readonly string[]): CharacterRunRequest {
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
  throw new Error('角色训练集仅支持 GPT 或 Precise Reference。')
}
