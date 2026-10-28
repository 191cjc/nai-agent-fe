import type { DatasetItem } from './api'
import { DATASET_PROMPTS } from './dataset-prompts'
import { compilePromptComments } from './prompt-weights'

export const MAX_DATASET_ITEMS = 300
export const MAX_DATASET_PROMPT_LENGTH = 1000
export const CUSTOM_CATEGORY = 'custom'

export interface DatasetEntry {
  id: string
  category: string
  prompt: string
  selected: boolean
}

export function defaultDatasetEntries(): DatasetEntry[] {
  return DATASET_PROMPTS.map(prompt => ({ ...prompt, selected: true }))
}

export function nextCustomId(entries: readonly DatasetEntry[]): string {
  let index = 1
  while (entries.some(entry => entry.id === `custom-${index}`)) index += 1
  return `custom-${index}`
}

function hasCommentLine(prompt: string): boolean {
  return prompt.split(/\r\n|\r|\n/).some(line => line.replace(/^[ \t]+/, '').startsWith('//'))
}

/** Mirrors the server definition rules so invalid runs never reach the paid POST. */
export function datasetItems(entries: readonly DatasetEntry[], stylePrompt: string): DatasetItem[] {
  const selected = entries.filter(entry => entry.selected)
  if (!selected.length) throw new Error('请至少选择一条训练集提示词。')
  if (selected.length > MAX_DATASET_ITEMS) throw new Error(`一次最多运行 ${MAX_DATASET_ITEMS} 条提示词。`)
  const style = compilePromptComments(stylePrompt).trim()
  if (!style) throw new Error('训练集批跑需要填写画风；画风会固定应用到每一条提示词。')
  const ids = new Set<string>()
  return selected.map((entry, index) => {
    const label = `第 ${index + 1} 条提示词`
    if (!/^[a-z0-9][a-z0-9-]*$/.test(entry.id) || entry.id.length > 64 || ids.has(entry.id)) throw new Error(`${label}编号无效，请重置后重试。`)
    ids.add(entry.id)
    if (!entry.prompt.trim()) throw new Error(`${label}为空。`)
    if (entry.prompt.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${label}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
    if (hasCommentLine(entry.prompt)) throw new Error(`${label}不能包含以 // 开头的注释行。`)
    if (style.length + 2 + entry.prompt.trim().length > 3000) throw new Error(`${label}与画风合计超过 3000 字符。`)
    return { id: entry.id, prompt: entry.prompt }
  })
}
