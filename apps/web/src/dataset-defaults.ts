// Prompt libraries load only with the lazy dataset panel, never in the main bundle.
import { CHARACTER_CATEGORIES, CHARACTER_PROMPTS } from './character-prompts'
import { DATASET_PROMPTS } from './dataset-prompts'
import type { DatasetEntry } from './dataset-run'

const FEMALE = /^(1girl|2girls|3girls|multiple girls)$/
const MALE = /^(1boy|2boys|multiple boys)$/
/** Default male items kept per category (~10% of the default set, operator 2026-10-30). */
const MALE_DEFAULTS: Record<string, number> = { portrait: 2, upper: 2, full: 2, scene: 2, light: 1, multi: 1 }

export type PromptGender = 'female' | 'male' | 'mixed' | 'none'

export function promptGender(prompt: string): PromptGender {
  const tags = prompt.split(',').map(tag => tag.trim())
  const female = tags.some(tag => FEMALE.test(tag))
  const male = tags.some(tag => MALE.test(tag))
  return female && male ? 'mixed' : male ? 'male' : female ? 'female' : 'none'
}

/**
 * Female-focused default: every female and no-human item, a few male items per
 * category, no mixed-gender items. Everything stays in the library for manual selection.
 */
export function defaultDatasetEntries(): DatasetEntry[] {
  const keptMale: Record<string, number> = {}
  return DATASET_PROMPTS.map(prompt => {
    const gender = promptGender(prompt.prompt)
    let selected = gender === 'female' || gender === 'none'
    if (gender === 'male') {
      keptMale[prompt.category] = (keptMale[prompt.category] ?? 0) + 1
      selected = keptMale[prompt.category] <= (MALE_DEFAULTS[prompt.category] ?? 0)
    }
    return { ...prompt, selected }
  })
}

export function defaultCharacterEntries(): DatasetEntry[] {
  const selected = new Set(CHARACTER_CATEGORIES.filter(category => category.defaultSelected).map(category => category.id))
  return CHARACTER_PROMPTS.map(prompt => ({ ...prompt, selected: selected.has(prompt.category) }))
}
