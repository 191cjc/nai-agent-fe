/**
 * Random style-dataset recipes: types mirroring apps/api/src/novelai_api/recipe_engine.py,
 * id generation, reference finding and bulk-edit helpers. Sampling itself runs on the
 * server (POST /api/dataset-recipes/sample) so previews and generation never disagree.
 */
import { TAG_ZH } from './prompt-zh'
import { compilePromptComments, parsePromptTags } from './prompt-weights'

export type Condition =
  | { all: Condition[] } | { any: Condition[] } | { not: Condition }
  | { chosen: string } | { partition_drawn: string }
  | { state: string; in: string[] } | { visible: string } | { tag: string }

export interface Region { id: string; label?: string; parent?: string | null }
export interface SlotValue { id: string; tag: string; label?: string; weight: number }
export interface Slot { id: string; label?: string; values: SlotValue[] }
export interface SlotUse {
  exclude?: string[]
  only?: string[] | null
  weight_mods?: Record<string, number>
  set_state?: string | null
  exclude_state?: string | null
}
export interface Effects {
  hide?: string[]
  set?: Record<string, string>
  consume?: Record<string, number>
  remove_partitions?: string[]
  remove_options?: string[]
  allow_options?: Record<string, string[]>
  allow_values?: Record<string, string[]>
  content_add?: string[]
  remove_tags?: string[]
  style_add?: string[]
  style_remove?: string[]
}
export interface WeightMod { when: Condition; factor: number }
export interface RecipeOption {
  id: string
  label?: string
  tags?: string
  weight: number
  weight_mods?: WeightMod[]
  when?: Condition | null
  needs?: string[]
  effects?: Effects
  slots?: Record<string, SlotUse>
  none?: boolean
  child?: boolean
  disabled?: boolean
  size?: 'portrait' | 'square' | 'landscape' | null
}
export interface Partition {
  id: string
  label?: string
  mode?: 'one' | 'fill'
  max_draws?: number
  quota?: boolean
  when?: Condition | null
  needs?: string[]
  options: RecipeOption[]
}
export interface Rule { id: string; label?: string; when: Condition; effects: Effects; disabled?: boolean }
export interface StyleTagBinding { tag: string; needs: string }
export interface Recipe {
  version: 1
  regions?: Region[]
  resources?: Record<string, number>
  states?: Record<string, string>
  slots?: Slot[]
  style_tags?: StyleTagBinding[]
  glossary?: Record<string, string>
  draw_order: string[]
  prompt_order?: string[] | null
  partitions: Partition[]
  rules?: Rule[]
}

export interface RecipeSummary { id: string; name: string; updated_at: number }
export interface StoredRecipe extends RecipeSummary { recipe: Recipe; created_at: number }

export interface DatasetDraw {
  partition: string
  option: string
  label: string
  values?: Record<string, string>
  reason?: string
}
export interface StyleEdits { add: string[]; remove: string[] }

export interface SampleItem {
  id: string
  prompt: string
  shape?: 'portrait' | 'square' | 'landscape' | null
  draws: DatasetDraw[]
  style_edits: StyleEdits
}
export interface OptionStat { option: string; label: string; target: number; count: number }
export interface PartitionStat {
  partition: string
  label: string
  options: OptionStat[]
  skips: Record<string, number>
  values: Record<string, Record<string, number>>
  quota_misses: number
}
export interface SampleStats {
  requested: number
  produced: number
  overflow: number
  stale_dependency: number
  partitions: PartitionStat[]
  rules: Record<string, number>
  style_removed: Record<string, number>
  style_added: Record<string, number>
  warnings: string[]
}
export interface SampleResult { items: SampleItem[]; stats: SampleStats }

export const DEFAULT_REGIONS: Region[] = [
  { id: 'person', label: '人物' },
  { id: 'face', label: '脸', parent: 'person' },
  { id: 'eyes', label: '眼睛', parent: 'face' },
  { id: 'upper', label: '上身', parent: 'person' },
  { id: 'lower', label: '下身', parent: 'person' },
  { id: 'feet', label: '脚', parent: 'lower' },
  { id: 'hands', label: '手', parent: 'person' },
]

export const SKIP_REASONS: Record<string, string> = {
  invisible: '不可见', condition: '条件不满足', conflict: '冲突', removed: '被移除',
}

export const EFFECT_LABELS: Record<keyof Effects, string> = {
  hide: '隐藏部位',
  set: '设置状态',
  consume: '占用资源',
  remove_partitions: '移除分区',
  remove_options: '移除选项',
  allow_options: '只允许选项',
  allow_values: '只允许取值',
  content_add: '加内容 tag（进 caption）',
  remove_tags: '删内容 tag',
  style_add: '加画风 tag（不进 caption）',
  style_remove: '删画风 tag',
}

/** List-valued effects that bulk add/remove can edit entry by entry. */
export const LIST_EFFECTS = ['hide', 'remove_partitions', 'remove_options', 'content_add', 'remove_tags', 'style_add', 'style_remove'] as const
export type ListEffect = typeof LIST_EFFECTS[number]

const ID_PREFIX = { partition: 'p', option: 'o', slot: 's', value: 'v', region: 'g', rule: 'r', resource: 'c', state: 'k' } as const
export type IdKind = keyof typeof ID_PREFIX

/** `<prefix>-<8 base36>` from 40 random bits; regenerated on collision within its scope. */
export function newId(kind: IdKind, taken: Iterable<string> = []): string {
  const used = new Set(taken)
  for (;;) {
    const bytes = crypto.getRandomValues(new Uint8Array(5))
    let value = 0
    for (const byte of bytes) value = value * 256 + byte
    const id = `${ID_PREFIX[kind]}-${value.toString(36).padStart(8, '0').slice(-8)}`
    if (!used.has(id)) return id
  }
}

export function emptyRecipe(): Recipe {
  return { version: 1, regions: DEFAULT_REGIONS.map(region => ({ ...region })), resources: {}, states: {}, slots: [], style_tags: [], glossary: {}, draw_order: [], prompt_order: [], partitions: [], rules: [] }
}

export function clone<T>(value: T): T {
  return structuredClone(value)
}

export function optionRef(partition: string, option: string): string {
  return `${partition}.${option}`
}

export function partitionLabel(recipe: Recipe, id: string): string {
  return recipe.partitions.find(part => part.id === id)?.label || id
}

export function optionLabel(recipe: Recipe, ref: string): string {
  const [partitionId, optionId] = ref.split('.')
  const part = recipe.partitions.find(item => item.id === partitionId)
  const option = part?.options.find(item => item.id === optionId)
  return `${part?.label || partitionId}.${option?.label || option?.tags || optionId}`
}

// ------------------------------------------------------------------ translations

export function splitTags(text: string): string[] {
  return text.split(/[,，\r\n]/).map(tag => tag.trim()).filter(Boolean)
}

const STYLE_NUMBER = /^[+-]?(?:\d+(?:\.\d+)?|\.\d+)::/
const MAX_STYLE_TAG_LENGTH = 300

/** Match recipe_style.py, including names inside zero/negative emphasis groups. */
function plainStyleTag(tag: string): string {
  return tag.replace(/(^|[\s,，([{]|(?<=::))[+-]?(?:\d+(?:\.\d+)?|\.\d+)::/g, '$1')
    .replace(/::/g, '').replace(/[{}[\]]/g, '').trim()
}

function styleTagKey(tag: string): string {
  return plainStyleTag(tag).replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
}

/** Strict for edits; tolerant when closing legacy baseline scopes before appending. */
function scanStyleTags(text: string, strict = true, rawPieces = false): { tags: string[]; suffix: string } {
  if (strict && text.includes('//')) throw new Error('画风增删不能包含 // 注释标记。')
  const scopes: Array<[string, string]> = []
  let inherited: Array<[string, string]> = []
  let piece = ''
  let parentheses = 0
  const result: string[] = []
  const emit = () => {
    if (rawPieces) {
      result.push(piece)
      return
    }
    const raw = piece.trim()
    if (!raw) return
    const tag = inherited.map(([opener]) => opener).join('') + raw + [...scopes].reverse().map(([, closer]) => closer).join('')
    if (styleTagKey(tag)) result.push(tag)
  }
  for (let index = 0; index < text.length;) {
    const character = text[index]
    if (character === '\\' && index + 1 < text.length) {
      piece += text.slice(index, index + 2)
      index += 2
      continue
    }
    const number = index === 0 || /[\s,，([{]/.test(text[index - 1]) || text.slice(index - 2, index) === '::' ? STYLE_NUMBER.exec(text.slice(index)) : null
    if (number) {
      piece += number[0]
      scopes.push([number[0], '::'])
      index += number[0].length
      continue
    }
    if (text.startsWith('::', index)) {
      if (scopes.at(-1)?.[1] !== '::') {
        if (strict) throw new Error('画风权重的 :: 分隔符不匹配。')
      } else scopes.pop()
      piece += '::'
      index += 2
      continue
    }
    if (character === '{' || character === '[') scopes.push([character, character === '{' ? '}' : ']'])
    else if (character === '}' || character === ']') {
      if (scopes.at(-1)?.[1] !== character) {
        if (strict) throw new Error('画风权重的括号不匹配。')
      } else scopes.pop()
    } else if (character === '(') parentheses += 1
    else if (character === ')') parentheses = Math.max(0, parentheses - 1)
    if (/[,，\n\r]/.test(character) && !parentheses) {
      emit()
      piece = ''
      inherited = [...scopes]
    } else piece += character
    index += 1
  }
  emit()
  return { tags: result, suffix: [...scopes].reverse().map(([, closer]) => closer).join('') }
}

/** Split shared emphasis into independently balanced tags, as on the server. */
export function splitStyleTags(text: string): string[] {
  return scanStyleTags(text).tags
}

/** Join legacy comma-split inputs before balancing their emphasis scopes. */
export function normalizeStyleTags(values: readonly string[], remove = false): string[] {
  const tags = splitStyleTags(values.join(', '))
  return remove ? tags.map(plainStyleTag) : tags
}

/** Validate frozen recipe edits before serializing a queued dataset item. */
export function validateStyleEdits(edits: StyleEdits, label: string): StyleEdits {
  const normalized: StyleEdits = { add: [], remove: [] }
  for (const field of ['add', 'remove'] as const) {
    const values = edits[field]
    const limit = field === 'add' ? 32 : 128
    const action = field === 'add' ? '新增' : '删除'
    if (!Array.isArray(values) || values.some(tag => typeof tag !== 'string' || !tag.trim())) throw new Error(`${label}的画风${action}项必须是非空 tag。`)
    try {
      normalized[field] = normalizeStyleTags(values, field === 'remove')
    } catch (error) {
      throw new Error(`${label}：${error instanceof Error ? error.message : '画风增删格式无效。'}`)
    }
    if (normalized[field].length > limit) throw new Error(`${label}的画风${action}拆分后最多 ${limit} 项。`)
    if (normalized[field].some(tag => [...tag].length > MAX_STYLE_TAG_LENGTH)) throw new Error(`${label}的单个画风${action} tag 不能超过 ${MAX_STYLE_TAG_LENGTH} 字符。`)
  }
  return normalized
}

/** Use the prompt editor's numeric-weight parser before comparing/displaying a tag. */
function plainTag(tag: string): string {
  const parsed = parsePromptTags(tag)
  return parsed.length === 1 ? parsed[0].text.trim() : tag.trim()
}

function tagKey(tag: string): string {
  return plainTag(tag).replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
}

/** Gloss of one plain tag: recipe glossary first, then the built-in dictionary. */
export function glossTag(recipe: Recipe, tag: string): string | null {
  const plain = plainTag(tag)
  const key = tagKey(plain)
  if (!key) return null
  return recipe.glossary?.[key] ?? recipe.glossary?.[plain] ?? TAG_ZH[key] ?? null
}

/** Tags of a text with `{slot}` placeholders substituted by a representative word. */
function glossTemplate(recipe: Recipe, text: string): Array<{ tag: string; zh: string | null }> {
  return splitTags(text).map(tag => {
    const plain = plainTag(tag.replace(/\{[a-z0-9-]+\}\s*/g, ''))
    const placeholder = /\{([a-z0-9-]+)\}/.exec(tag)
    const slot = placeholder ? recipe.slots?.find(item => item.id === placeholder[1]) : undefined
    const base = glossTag(recipe, plain)
    return { tag, zh: base === null ? null : `${slot ? `[${slot.label || slot.id}]` : ''}${base}` }
  })
}

export function glossOption(recipe: Recipe, option: RecipeOption): Array<{ tag: string; zh: string | null }> {
  return glossTemplate(recipe, option.tags ?? '')
}

/** Every English tag in the recipe that has no gloss (deduplicated, placeholders removed). */
export function missingGlosses(recipe: Recipe): string[] {
  const missing = new Set<string>()
  const check = (tag: string) => {
    const plain = plainTag(tag.replace(/\{[a-z0-9-]+\}\s*/g, ''))
    if (plain && glossTag(recipe, plain) === null) missing.add(plain)
  }
  for (const part of recipe.partitions) {
    for (const option of part.options) {
      splitTags(option.tags ?? '').forEach(check)
      for (const key of ['content_add', 'remove_tags', 'style_add', 'style_remove'] as const) option.effects?.[key]?.forEach(check)
    }
  }
  for (const rule of recipe.rules ?? []) {
    for (const key of ['content_add', 'remove_tags', 'style_add', 'style_remove'] as const) rule.effects[key]?.forEach(check)
  }
  for (const slot of recipe.slots ?? []) for (const value of slot.values) check(value.tag)
  for (const binding of recipe.style_tags ?? []) check(binding.tag)
  return [...missing]
}

// ------------------------------------------------------------------ references

export interface Reference { where: string; text: string; remove: (recipe: Recipe) => void }

function conditionRefs(condition: Condition | null | undefined, target: (c: Condition) => boolean): boolean {
  if (!condition) return false
  if (target(condition)) return true
  if ('all' in condition) return condition.all.some(child => conditionRefs(child, target))
  if ('any' in condition) return condition.any.some(child => conditionRefs(child, target))
  if ('not' in condition) return conditionRefs(condition.not, target)
  return false
}

/** Remove matching leaves; empty all/any collapse; returns null when nothing is left. */
export function pruneCondition(condition: Condition | null | undefined, target: (c: Condition) => boolean): Condition | null {
  if (!condition || target(condition)) return null
  if ('all' in condition || 'any' in condition) {
    const key = 'all' in condition ? 'all' : 'any'
    const children = ('all' in condition ? condition.all : (condition as { any: Condition[] }).any)
      .map(child => pruneCondition(child, target)).filter((child): child is Condition => child !== null)
    if (!children.length) return null
    return children.length === 1 ? children[0] : (key === 'all' ? { all: children } : { any: children })
  }
  if ('not' in condition) {
    const inner = pruneCondition(condition.not, target)
    return inner ? { not: inner } : null
  }
  return condition
}

type Owner = { where: string; rule?: string; get: (recipe: Recipe) => { when?: Condition | null; effects?: Effects; weight_mods?: WeightMod[] } | undefined }

function owners(recipe: Recipe): Owner[] {
  const list: Owner[] = []
  for (const part of recipe.partitions) {
    list.push({ where: `分区「${part.label || part.id}」条件`, get: r => r.partitions.find(p => p.id === part.id) })
    for (const option of part.options) {
      list.push({ where: `选项「${part.label || part.id}.${option.label || option.id}」`, get: r => r.partitions.find(p => p.id === part.id)?.options.find(o => o.id === option.id) })
    }
  }
  for (const rule of recipe.rules ?? []) list.push({ where: `规则「${rule.label || rule.id}」`, rule: rule.id, get: r => r.rules?.find(item => item.id === rule.id) })
  return list
}

/** Everything that points at a partition (`option` absent) or one option. */
export function findReferences(recipe: Recipe, partitionId: string, optionId?: string): Reference[] {
  const ref = optionId === undefined ? null : optionRef(partitionId, optionId)
  const hitsCondition = (c: Condition) => ref !== null
    ? 'chosen' in c && c.chosen === ref
    : ('chosen' in c && c.chosen.split('.')[0] === partitionId) || ('partition_drawn' in c && c.partition_drawn === partitionId)
  const result: Reference[] = []
  for (const owner of owners(recipe)) {
    const target = owner.get(recipe)
    if (!target) continue
    if (conditionRefs(target.when, hitsCondition)) {
      // A rule needs a condition: one left with none would fire on every item, so it goes too.
      result.push({ where: owner.where, text: owner.rule ? '条件（条件删空时删除整条规则）' : '条件', remove: r => {
        const t = owner.get(r)
        if (!t) return
        t.when = pruneCondition(t.when, hitsCondition)
        if (owner.rule && !t.when) r.rules = (r.rules ?? []).filter(rule => rule.id !== owner.rule)
      } })
    }
    if (target.weight_mods?.some(mod => conditionRefs(mod.when, hitsCondition))) {
      result.push({ where: owner.where, text: '条件权重', remove: r => { const t = owner.get(r); if (t?.weight_mods) t.weight_mods = t.weight_mods.filter(mod => !conditionRefs(mod.when, hitsCondition)) } })
    }
    const effects = target.effects
    if (!effects) continue
    if (ref === null) {
      if (effects.remove_partitions?.includes(partitionId)) result.push({ where: owner.where, text: '移除分区', remove: r => { const e = owner.get(r)?.effects; if (e?.remove_partitions) e.remove_partitions = e.remove_partitions.filter(id => id !== partitionId) } })
      if (effects.allow_options?.[partitionId]) result.push({ where: owner.where, text: '只允许选项', remove: r => { const e = owner.get(r)?.effects; if (e?.allow_options) delete e.allow_options[partitionId] } })
      if (effects.remove_options?.some(item => item.startsWith(`${partitionId}.`))) result.push({ where: owner.where, text: '移除选项', remove: r => { const e = owner.get(r)?.effects; if (e?.remove_options) e.remove_options = e.remove_options.filter(item => !item.startsWith(`${partitionId}.`)) } })
      for (const key of Object.keys(effects.allow_values ?? {})) if (key.startsWith(`${partitionId}.`)) result.push({ where: owner.where, text: '只允许取值', remove: r => { const e = owner.get(r)?.effects; if (e?.allow_values) delete e.allow_values[key] } })
    } else {
      if (effects.remove_options?.includes(ref)) result.push({ where: owner.where, text: '移除选项', remove: r => { const e = owner.get(r)?.effects; if (e?.remove_options) e.remove_options = e.remove_options.filter(item => item !== ref) } })
      if (effects.allow_options?.[partitionId]?.includes(optionId!)) result.push({ where: owner.where, text: '只允许选项', remove: r => {
        const e = owner.get(r)?.effects
        const list = e?.allow_options?.[partitionId]
        if (e?.allow_options && list) {
          const next = list.filter(id => id !== optionId)
          if (next.length) e.allow_options[partitionId] = next
          else delete e.allow_options[partitionId]
        }
      } })
      for (const key of Object.keys(effects.allow_values ?? {})) if (key.startsWith(`${ref}.`)) result.push({ where: owner.where, text: '只允许取值', remove: r => { const e = owner.get(r)?.effects; if (e?.allow_values) delete e.allow_values[key] } })
    }
  }
  return result
}

export function deletePartition(recipe: Recipe, partitionId: string): void {
  for (const reference of findReferences(recipe, partitionId)) reference.remove(recipe)
  recipe.partitions = recipe.partitions.filter(part => part.id !== partitionId)
  recipe.draw_order = recipe.draw_order.filter(id => id !== partitionId)
  if (recipe.prompt_order) recipe.prompt_order = recipe.prompt_order.filter(id => id !== partitionId)
}

export function deleteOption(recipe: Recipe, partitionId: string, optionId: string): void {
  for (const reference of findReferences(recipe, partitionId, optionId)) reference.remove(recipe)
  const part = recipe.partitions.find(item => item.id === partitionId)
  if (part) part.options = part.options.filter(option => option.id !== optionId)
}

// ------------------------------------------------------------------ bulk edits

export interface BulkTarget { partition: string; option: string }

export function targetOptions(recipe: Recipe, targets: readonly BulkTarget[]): RecipeOption[] {
  return targets.flatMap(target => {
    const option = recipe.partitions.find(part => part.id === target.partition)?.options.find(item => item.id === target.option)
    return option ? [option] : []
  })
}

/** Add or remove one entry of a list effect; returns [changed, skipped]. Idempotent. */
export function bulkListEffect(options: RecipeOption[], key: ListEffect, value: string, mode: 'add' | 'remove'): [number, number] {
  let changed = 0
  let skipped = 0
  const normalized = value.trim()
  for (const option of options) {
    const effects = option.effects ?? (option.effects = {})
    const list = effects[key] ?? []
    const has = list.some(item => item.toLowerCase() === normalized.toLowerCase())
    if (mode === 'add' ? has : !has) { skipped += 1; continue }
    effects[key] = mode === 'add' ? [...list, normalized] : list.filter(item => item.toLowerCase() !== normalized.toLowerCase())
    changed += 1
  }
  return [changed, skipped]
}

export function bulkAllowOptions(options: RecipeOption[], partition: string, allowed: string[], mode: 'add' | 'remove'): [number, number] {
  let changed = 0
  let skipped = 0
  for (const option of options) {
    const effects = option.effects ?? (option.effects = {})
    const map = effects.allow_options ?? (effects.allow_options = {})
    const same = JSON.stringify([...(map[partition] ?? [])].sort()) === JSON.stringify([...allowed].sort())
    if (mode === 'add') {
      if (same) { skipped += 1; continue }
      map[partition] = [...allowed]
    } else {
      if (!map[partition]) { skipped += 1; continue }
      delete map[partition]
    }
    changed += 1
  }
  return [changed, skipped]
}

const sameCondition = (a: Condition, b: Condition) => JSON.stringify(a) === JSON.stringify(b)

/** AND a clause into every option's condition, or remove that exact clause. */
export function bulkCondition(options: RecipeOption[], clause: Condition, mode: 'add' | 'remove'): [number, number] {
  let changed = 0
  let skipped = 0
  for (const option of options) {
    const current = option.when ?? null
    const clauses = current === null ? [] : 'all' in current ? current.all : [current]
    const has = clauses.some(item => sameCondition(item, clause))
    if (mode === 'add' ? has : !has) { skipped += 1; continue }
    const next = mode === 'add' ? [...clauses, clause] : clauses.filter(item => !sameCondition(item, clause))
    option.when = next.length === 0 ? null : next.length === 1 ? next[0] : { all: next }
    changed += 1
  }
  return [changed, skipped]
}

export function bulkWeight(options: RecipeOption[], mode: 'set' | 'multiply' | 'normalize', value: number): void {
  if (mode === 'set') options.forEach(option => { option.weight = value })
  else if (mode === 'multiply') options.forEach(option => { option.weight = Math.max(0.001, option.weight * value) })
  else {
    const total = options.reduce((sum, option) => sum + option.weight, 0)
    if (total > 0) options.forEach(option => { option.weight = Math.max(0.001, Number((option.weight / total * value).toFixed(3))) })
  }
}

export function moveOrCopy(recipe: Recipe, targets: readonly BulkTarget[], destination: string, copy: boolean): number {
  const part = recipe.partitions.find(item => item.id === destination)
  if (!part) return 0
  let count = 0
  for (const target of targets) {
    if (target.partition === destination && !copy) continue
    const source = recipe.partitions.find(item => item.id === target.partition)
    const option = source?.options.find(item => item.id === target.option)
    if (!source || !option || option.none) continue
    const taken = part.options.map(item => item.id)
    const moved = clone(option)
    if (copy || taken.includes(moved.id)) moved.id = newId('option', taken)
    if (!copy) {
      // References follow the option to its new partition.
      const oldRef = optionRef(source.id, option.id)
      const newRef = optionRef(destination, moved.id)
      renameReferences(recipe, oldRef, newRef)
      source.options = source.options.filter(item => item !== option)
    }
    part.options.push(moved)
    count += 1
  }
  return count
}

function renameReferences(recipe: Recipe, oldRef: string, newRef: string): void {
  const [oldPart, oldOption] = oldRef.split('.')
  const [newPart, newOption] = newRef.split('.')
  const walk = (condition: Condition | null | undefined): void => {
    if (!condition) return
    if ('chosen' in condition && condition.chosen === oldRef) (condition as { chosen: string }).chosen = newRef
    if ('all' in condition) condition.all.forEach(walk)
    if ('any' in condition) condition.any.forEach(walk)
    if ('not' in condition) walk(condition.not)
  }
  const targets = [
    ...recipe.partitions.flatMap(part => [part, ...part.options]),
    ...(recipe.rules ?? []),
  ] as Array<{ when?: Condition | null; effects?: Effects; weight_mods?: WeightMod[] }>
  for (const target of targets) {
    walk(target.when)
    target.weight_mods?.forEach(mod => walk(mod.when))
    const effects = target.effects
    if (!effects) continue
    if (effects.remove_options) effects.remove_options = effects.remove_options.map(item => item === oldRef ? newRef : item)
    const allowed = effects.allow_options?.[oldPart]
    if (allowed?.includes(oldOption)) {
      effects.allow_options![oldPart] = allowed.filter(id => id !== oldOption)
      if (!effects.allow_options![oldPart].length) delete effects.allow_options![oldPart]
      effects.allow_options![newPart] = [...(effects.allow_options![newPart] ?? []), newOption]
    }
    for (const key of Object.keys(effects.allow_values ?? {})) {
      if (key.startsWith(`${oldRef}.`)) {
        effects.allow_values![`${newRef}.${key.slice(oldRef.length + 1)}`] = effects.allow_values![key]
        delete effects.allow_values![key]
      }
    }
  }
}

/** Short Chinese summary of a condition for display. */
export function describeCondition(recipe: Recipe, condition: Condition | null | undefined): string {
  if (!condition) return ''
  if ('all' in condition) return condition.all.map(child => describeCondition(recipe, child)).join(' 且 ')
  if ('any' in condition) return `(${condition.any.map(child => describeCondition(recipe, child)).join(' 或 ')})`
  if ('not' in condition) return `不满足（${describeCondition(recipe, condition.not)}）`
  if ('chosen' in condition) return `选了 ${optionLabel(recipe, condition.chosen)}`
  if ('partition_drawn' in condition) return `${partitionLabel(recipe, condition.partition_drawn)} 有结果`
  if ('state' in condition) return `${recipe.states?.[condition.state] || condition.state} 是 ${condition.in.join(' 或 ')}`
  if ('visible' in condition) return `${recipe.regions?.find(region => region.id === condition.visible)?.label || condition.visible} 可见`
  if ('tag' in condition) return `内容含 ${condition.tag}`
  return ''
}

export function describeEffects(recipe: Recipe, effects: Effects | undefined): string[] {
  if (!effects) return []
  const regions = (ids: string[]) => ids.map(id => recipe.regions?.find(region => region.id === id)?.label || id).join('、')
  const parts: string[] = []
  if (effects.hide?.length) parts.push(`隐藏 ${regions(effects.hide)}`)
  if (effects.set && Object.keys(effects.set).length) parts.push(`状态 ${Object.entries(effects.set).map(([k, v]) => `${recipe.states?.[k] || k}=${v}`).join('、')}`)
  if (effects.consume && Object.keys(effects.consume).length) parts.push(`占用 ${Object.entries(effects.consume).map(([k, v]) => `${k}×${v}`).join('、')}`)
  if (effects.remove_partitions?.length) parts.push(`移除分区 ${effects.remove_partitions.map(id => partitionLabel(recipe, id)).join('、')}`)
  if (effects.remove_options?.length) parts.push(`移除 ${effects.remove_options.map(ref => optionLabel(recipe, ref)).join('、')}`)
  for (const [part, ids] of Object.entries(effects.allow_options ?? {})) parts.push(`只允许 ${partitionLabel(recipe, part)}=[${ids.map(id => optionLabel(recipe, `${part}.${id}`).split('.')[1]).join('、')}]`)
  for (const [key, ids] of Object.entries(effects.allow_values ?? {})) parts.push(`只允许 ${key}=[${ids.join('、')}]`)
  if (effects.content_add?.length) parts.push(`+内容 ${effects.content_add.join(', ')}`)
  if (effects.remove_tags?.length) parts.push(`−内容 ${effects.remove_tags.join(', ')}`)
  if (effects.style_add?.length) parts.push(`+画风 ${effects.style_add.join(', ')}`)
  if (effects.style_remove?.length) parts.push(`−画风 ${effects.style_remove.join(', ')}`)
  return parts
}

/** Apply style edits locally for display only (the server resolves the real style). */
export function previewStyle(style: string, edits: StyleEdits | undefined): string {
  if (!edits || (!edits.add.length && !edits.remove.length)) return style
  const remove = new Set(normalizeStyleTags(edits.remove, true).map(styleTagKey))
  const present = new Set<string>()
  // Keep the scope markers surrounding a removed member so other members of a
  // shared weight/emphasis group retain their original weights, as on the server.
  const lines = style.split('\n').map(line => {
    if (line.trimStart().startsWith('//')) return line
    const kept: string[] = []
    for (const piece of scanStyleTags(line, false, true).tags) {
      const opener = /^(?:\s*(?:[{[]|[+-]?(?:\d+(?:\.\d+)?|\.\d+)::))*/.exec(piece)![0]
      const rest = piece.slice(opener.length)
      const closer = /(?:(?:[}\]]|::)\s*)*$/.exec(rest)![0]
      const body = closer ? rest.slice(0, -closer.length) : rest
      const key = styleTagKey(body)
      if (key && remove.has(key)) {
        if (opener.trim() || closer.trim()) kept.push(`${kept.length ? ' ' : ''}${opener.trim()}${closer.trim()}`)
      } else {
        if (key) present.add(key)
        kept.push(piece)
      }
    }
    return kept.join(',')
  })
  let result = lines.join('\n').replace(/(,\s*)+,/g, ',').replace(/^\s*,\s*/gm, '').replace(/\s*,\s*$/gm, '')
  const additions: string[] = []
  for (const tag of normalizeStyleTags(edits.add)) {
    const key = styleTagKey(tag)
    if (key && !present.has(key)) {
      present.add(key)
      additions.push(tag.trim())
    }
  }
  if (additions.length) {
    const visible = compilePromptComments(result)
    const suffix = scanStyleTags(visible, false).suffix
    let base = result.trimEnd()
    if (suffix) base += `${base.split('\n').at(-1)!.trimStart().startsWith('//') ? '\n' : ' '}${suffix}`
    let joiner = visible.trim() ? ', ' : ''
    if (base.split('\n').at(-1)!.trimStart().startsWith('//')) joiner = '\n'
    result = `${base}${joiner}${additions.join(', ')}`
  }
  return result
}
