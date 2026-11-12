// Prompt libraries load only with the lazy dataset panel, never in the main bundle.
import { characterCategories, characterPrompts, type CharacterMode } from './character-prompts'
import type { DatasetEntry } from './dataset-run'

/** The fixed style library was retired (2026-11-12): style drafts come from random recipes. */
export function defaultDatasetEntries(): DatasetEntry[] {
  return []
}

export function defaultCharacterEntries(mode: CharacterMode = 'gpt'): DatasetEntry[] {
  const selected = new Set(characterCategories(mode).filter(category => category.defaultSelected).map(category => category.id))
  return characterPrompts(mode).map(prompt => ({ ...prompt, selected: selected.has(prompt.category) }))
}
