import type { GenerationRequest } from './api'

export const SHARED_SECTION_KEYS = ['scene', 'other'] as const
export const CHARACTER_SECTION_KEYS = ['character', 'upper_clothing', 'lower_clothing', 'action', 'tags', 'special', 'other'] as const
export type SharedSectionKey = typeof SHARED_SECTION_KEYS[number]
export type CharacterSectionKey = typeof CHARACTER_SECTION_KEYS[number]
export const SECTION_LABELS = {
  scene: '场景', character: '角色', upper_clothing: '上半身服饰', lower_clothing: '下半身服饰',
  action: '动作', tags: '标签', special: '特殊', other: '其他',
} as const
export interface PromptSection { text: string; enabled: boolean }
export type SharedSections = Record<SharedSectionKey, PromptSection>
export type CharacterSections = Record<CharacterSectionKey, PromptSection>
export interface SectionCharacter { sections: CharacterSections; x: number; y: number }
export interface PromptSections { version: 1; shared: SharedSections; characters: SectionCharacter[] }
export interface SectionCharacterDraft extends SectionCharacter { id: string }
export interface SectionDraft { shared_sections: SharedSections; character_prompts: SectionCharacterDraft[]; style_prompt: string }
export type SectionReference = { scope: 'shared'; section: SharedSectionKey }
  | { scope: 'character'; characterId: string; section: CharacterSectionKey }
export type PromptSnapshotEntry = { scope: 'shared'; section: SharedSectionKey; text: string }
  | { scope: 'character'; character_index: number; section: CharacterSectionKey; text: string }
export interface PromptSnapshotCreate { id: string; name: string; entries: PromptSnapshotEntry[] }
export interface PromptSnapshot extends PromptSnapshotCreate { created_at: number }
export interface PromptSnapshotSummary { id: string; name: string; created_at: number; entry_count: number }
export interface PromptSnapshotPage { items: PromptSnapshotSummary[]; next_offset: number | null }
export type SnapshotImportMode = 'append' | 'replace'

export function emptySharedSections(text = ''): SharedSections {
  return { scene: { text: '', enabled: true }, other: { text, enabled: true } }
}
export function emptyCharacterSections(text = ''): CharacterSections {
  return {
    character: { text: '', enabled: true }, upper_clothing: { text: '', enabled: true }, lower_clothing: { text: '', enabled: true },
    action: { text: '', enabled: true }, tags: { text: '', enabled: true }, special: { text: '', enabled: true }, other: { text, enabled: true },
  }
}
export function copySharedSections(sections: SharedSections): SharedSections {
  return { scene: { ...sections.scene }, other: { ...sections.other } }
}
export function copyCharacterSections(sections: CharacterSections): CharacterSections {
  return Object.fromEntries(CHARACTER_SECTION_KEYS.map(key => [key, { ...sections[key] }])) as CharacterSections
}
export function composeSections<Key extends string>(sections: Record<Key, PromptSection>, keys: readonly Key[]): string {
  const parts = keys.map(key => sections[key]).filter(section => section.enabled && section.text.trim()).map(section => section.text)
  return parts.length === 1 ? parts[0] : parts.map(text => text.trim()).join(', ')
}
export const sharedPrompt = (sections: SharedSections): string => composeSections(sections, SHARED_SECTION_KEYS)
export const characterPrompt = (sections: CharacterSections): string => composeSections(sections, CHARACTER_SECTION_KEYS)

export function metadataFromDraft(draft: SectionDraft): PromptSections {
  return {
    version: 1, shared: copySharedSections(draft.shared_sections),
    characters: draft.character_prompts.map(({ sections, x, y }) => ({ sections: copyCharacterSections(sections), x, y })),
  }
}
export function copyPromptMetadata(metadata: PromptSections): PromptSections {
  return { version: 1, shared: copySharedSections(metadata.shared), characters: metadata.characters.map(person => ({
    sections: copyCharacterSections(person.sections), x: person.x, y: person.y,
  })) }
}

/** Import can be valid before model/settings/base text are filled in. */
export function validateSectionBudgets(draft: SectionDraft): void {
  if (draft.character_prompts.length > 6) throw new Error('最多添加 6 个人物，草稿未修改。')
  const allSections = [...SHARED_SECTION_KEYS.map(key => draft.shared_sections[key]),
    ...draft.character_prompts.flatMap(person => CHARACTER_SECTION_KEYS.map(key => person.sections[key]))]
  if (allSections.some(section => section.text.length > 3000)) throw new Error('每个分区不能超过 3000 字符，草稿未修改。')
  const shared = sharedPrompt(draft.shared_sections)
  const base = draft.style_prompt.trim() ? [draft.style_prompt.trim(), shared.trim()].filter(Boolean).join(', ') : shared
  if (draft.style_prompt.length > 3000 || shared.length > 3000 || base.length > 3000) {
    throw new Error('画风和公共提示词合计不能超过 3000 字符（含分隔符），草稿未修改。')
  }
  if (draft.character_prompts.some(person => characterPrompt(person.sections).length > 3000)) {
    throw new Error('每个人物启用的提示词合计不能超过 3000 字符（含分隔符），草稿未修改。')
  }
  if (draft.character_prompts.some(person => !validAxis(person.x) || !validAxis(person.y))) throw new Error('人物位置无效，草稿未修改。')
}

const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const exactKeys = (value: Record<string, unknown>, keys: readonly string[]) => Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key))
const validAxis = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0.1 && value <= 0.9
function validSections(value: unknown, keys: readonly string[]): boolean {
  return object(value) && exactKeys(value, keys) && keys.every(key => {
    const section = value[key]
    return object(section) && exactKeys(section, ['text', 'enabled']) && typeof section.text === 'string' && section.text.length <= 3000 && typeof section.enabled === 'boolean'
  })
}
export function isPromptSections(value: unknown): value is PromptSections {
  return object(value) && exactKeys(value, ['version', 'shared', 'characters']) && value.version === 1
    && validSections(value.shared, SHARED_SECTION_KEYS) && Array.isArray(value.characters) && value.characters.length <= 6
    && value.characters.every(person => object(person) && exactKeys(person, ['sections', 'x', 'y'])
      && validAxis(person.x) && validAxis(person.y) && validSections(person.sections, CHARACTER_SECTION_KEYS))
}
/** New metadata is a strict payload projection, never a best-effort fallback. */
export function validRequestSections(parameters: GenerationRequest): boolean {
  const metadata = parameters.prompt_sections
  if (metadata === undefined || metadata === null) return true
  if (!isPromptSections(metadata) || typeof parameters.style_prompt !== 'string') return false
  const shared = sharedPrompt(metadata.shared)
  const base = parameters.style_prompt.trim() ? [parameters.style_prompt.trim(), shared.trim()].filter(Boolean).join(', ') : shared
  if (parameters.positive_prompt !== shared || shared.length > 3000 || parameters.style_prompt.length > 3000 || base.length > 3000 || !base.trim()) return false
  const characters = metadata.characters.map(person => ({ prompt: characterPrompt(person.sections), x: person.x, y: person.y })).filter(person => person.prompt.trim())
  if (characters.some(person => person.prompt.length > 3000)) return false
  return Array.isArray(parameters.character_prompts) && characters.length === parameters.character_prompts.length
    && characters.every((person, index) => {
      const effective = parameters.character_prompts[index]
      return effective?.prompt === person.prompt && (effective.x === undefined ? 0.5 : effective.x) === person.x
        && (effective.y === undefined ? 0.5 : effective.y) === person.y
    })
}
export function restoredSections(parameters: GenerationRequest): PromptSections {
  if (!validRequestSections(parameters)) throw new Error('保存的提示词分区无效，草稿未修改。')
  if (parameters.prompt_sections) return copyPromptMetadata(parameters.prompt_sections)
  return { version: 1, shared: emptySharedSections(parameters.positive_prompt), characters: (parameters.character_prompts ?? []).map(person => ({
    sections: emptyCharacterSections(person.prompt), x: person.x ?? 0.5, y: person.y ?? 0.5,
  })) }
}

export function sectionReferenceKey(reference: SectionReference): string {
  return reference.scope === 'shared' ? `shared:${reference.section}` : `character:${reference.characterId}:${reference.section}`
}
export function sectionAt(draft: SectionDraft, reference: SectionReference): PromptSection | undefined {
  return reference.scope === 'shared' ? draft.shared_sections[reference.section]
    : draft.character_prompts.find(person => person.id === reference.characterId)?.sections[reference.section]
}
export function snapshotEntries(draft: SectionDraft, references: SectionReference[]): PromptSnapshotEntry[] {
  const seen = new Set<string>()
  return references.map(reference => {
    const key = sectionReferenceKey(reference)
    const section = sectionAt(draft, reference)
    if (!section || seen.has(key)) throw new Error('所选分区已变化，请重新选择。')
    seen.add(key)
    if (reference.scope === 'shared') return { scope: 'shared', section: reference.section, text: section.text }
    const index = draft.character_prompts.findIndex(person => person.id === reference.characterId)
    return { scope: 'character', character_index: index, section: reference.section, text: section.text }
  })
}
export function isSnapshotEntry(value: unknown): value is PromptSnapshotEntry {
  if (!object(value) || typeof value.text !== 'string' || value.text.length > 3000) return false
  if (value.scope === 'shared') return exactKeys(value, ['scope', 'section', 'text']) && SHARED_SECTION_KEYS.some(key => key === value.section)
  return value.scope === 'character' && exactKeys(value, ['scope', 'character_index', 'section', 'text'])
    && typeof value.character_index === 'number' && Number.isInteger(value.character_index) && value.character_index >= 0 && value.character_index < 6
    && CHARACTER_SECTION_KEYS.some(key => key === value.section)
}
export const isSnapshotId = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value)
export function isSnapshot(value: unknown): value is PromptSnapshot {
  if (!object(value) || !exactKeys(value, ['id', 'name', 'entries', 'created_at']) || !isSnapshotId(value.id)
    || typeof value.name !== 'string' || !value.name.trim() || value.name.length > 100 || typeof value.created_at !== 'number' || !Number.isInteger(value.created_at)
    || !Array.isArray(value.entries) || !value.entries.length || value.entries.length > 44 || !value.entries.every(isSnapshotEntry)) return false
  const keys = value.entries.map(entry => `${entry.scope}:${entry.scope === 'character' ? entry.character_index : ''}:${entry.section}`)
  return new Set(keys).size === keys.length && value.entries.some(entry => entry.text.trim())
}
export function isSnapshotPage(value: unknown): value is PromptSnapshotPage {
  return object(value) && exactKeys(value, ['items', 'next_offset']) && Array.isArray(value.items) && value.items.length <= 100 && value.items.every(item => object(item)
    && exactKeys(item, ['id', 'name', 'created_at', 'entry_count'])
    && isSnapshotId(item.id) && typeof item.name === 'string' && Boolean(item.name.trim()) && item.name.length <= 100
    && typeof item.created_at === 'number' && Number.isInteger(item.created_at) && typeof item.entry_count === 'number'
    && Number.isInteger(item.entry_count) && item.entry_count >= 1 && item.entry_count <= 44)
    && (value.next_offset === null || (typeof value.next_offset === 'number' && Number.isSafeInteger(value.next_offset) && value.next_offset >= 0))
}
export function snapshotGroupKey(snapshotId: string, index: number): string { return `${snapshotId}:${index}` }
export function compatibleEntries(snapshot: PromptSnapshot, destination: SectionReference): PromptSnapshotEntry[] {
  return snapshot.entries.filter(entry => entry.scope === destination.scope && entry.section === destination.section)
}

/** Work on independent copies and commit only the fully validated projection. */
export function projectSnapshotImport(draft: SectionDraft, snapshots: PromptSnapshot[], mode: SnapshotImportMode,
  mappings: Record<string, string>, createPerson: () => SectionCharacterDraft, destination?: SectionReference): Pick<SectionDraft, 'shared_sections' | 'character_prompts'> {
  if (!snapshots.length || snapshots.some(snapshot => !isSnapshot(snapshot))) throw new Error('请重新选择有效快照，草稿未修改。')
  if (mode !== 'append' && mode !== 'replace') throw new Error('请选择导入方式。')
  const next: SectionDraft = {
    style_prompt: draft.style_prompt, shared_sections: copySharedSections(draft.shared_sections),
    character_prompts: draft.character_prompts.map(person => ({ ...person, sections: copyCharacterSections(person.sections) })),
  }
  if (destination && !sectionAt(next, destination)) throw new Error('目标分区已被移除，请重新选择，草稿未修改。')
  for (const snapshot of snapshots) {
    const entries = destination ? compatibleEntries(snapshot, destination) : snapshot.entries
    if (!entries.length) throw new Error(`“${snapshot.name}”没有匹配的分区，草稿未修改。`)
    const groups = new Map<number, string>()
    for (const entry of entries) {
      let target: SectionReference
      if (destination) target = destination
      else if (entry.scope === 'shared') target = { scope: 'shared', section: entry.section }
      else {
        let id = groups.get(entry.character_index)
        if (!id) {
          const mapping = mappings[snapshotGroupKey(snapshot.id, entry.character_index)]
          if (mapping === 'new') {
            const person = createPerson()
            next.character_prompts.push(person)
            id = person.id
          } else id = next.character_prompts.find(person => person.id === mapping)?.id
          if (!id) throw new Error('请选择每组人物的有效导入目标，草稿未修改。')
          groups.set(entry.character_index, id)
        }
        target = { scope: 'character', characterId: id, section: entry.section }
      }
      const section = sectionAt(next, target)
      if (!section) throw new Error('目标分区已失效，草稿未修改。')
      // Preserve exact replacement/single text; append never deduplicates tags.
      section.text = mode === 'replace' ? entry.text
        : [section.text, entry.text].filter(text => text.trim()).join(', ')
    }
  }
  validateSectionBudgets(next)
  return { shared_sections: next.shared_sections, character_prompts: next.character_prompts }
}
