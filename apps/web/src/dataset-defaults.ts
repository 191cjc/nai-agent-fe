// Prompt libraries load only with the lazy dataset panel, never in the main bundle.
import { CHARACTER_CATEGORIES, CHARACTER_PROMPTS } from './character-prompts'
import { DATASET_PROMPTS } from './dataset-prompts'
import type { DatasetEntry } from './dataset-run'

/** Every library item is a default since 2026-10-31 (non-default items were removed). */
export function defaultDatasetEntries(): DatasetEntry[] {
  return DATASET_PROMPTS.map(prompt => ({ ...prompt, selected: true }))
}

export function defaultCharacterEntries(): DatasetEntry[] {
  const selected = new Set(CHARACTER_CATEGORIES.filter(category => category.defaultSelected).map(category => category.id))
  return CHARACTER_PROMPTS.map(prompt => ({ ...prompt, selected: selected.has(prompt.category) }))
}
