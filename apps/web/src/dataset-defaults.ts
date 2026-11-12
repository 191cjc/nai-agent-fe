// Prompt libraries load only with the lazy dataset panel, never in the main bundle.
import { characterCategories, characterPrompts, type CharacterMode } from './character-prompts'
import { DATASET_PROMPTS } from './dataset-prompts'
import type { DatasetEntry } from './dataset-run'

/** Every library item is a default since 2026-10-31 (non-default items were removed). */
export function defaultDatasetEntries(): DatasetEntry[] {
  return DATASET_PROMPTS.map(prompt => ({ ...prompt, selected: true }))
}

export function defaultCharacterEntries(mode: CharacterMode = 'gpt'): DatasetEntry[] {
  const selected = new Set(characterCategories(mode).filter(category => category.defaultSelected).map(category => category.id))
  return characterPrompts(mode).map(prompt => ({ ...prompt, selected: selected.has(prompt.category) }))
}
