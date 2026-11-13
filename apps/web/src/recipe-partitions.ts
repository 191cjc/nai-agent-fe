/**
 * Partition-level JSON import/export for random recipes.
 *
 * A bundle carries the chosen partitions plus what they depend on (slots, regions,
 * resources, state labels, glossary). Import only adds or replaces the chosen
 * partitions; recipe-level definitions are only ever added, never overwritten. A
 * reference that the merged recipe cannot satisfy is removed and reported so the
 * result saves cleanly (the server still validates on save).
 */
import { clone, findReferences, type Condition, type Effects, type Partition, type Recipe, type Region, type Slot, type WeightMod } from './recipe'

export const PARTITION_BUNDLE_FORMAT = 'nai-recipe-partitions'

export interface PartitionBundle {
  format: typeof PARTITION_BUNDLE_FORMAT
  version: 1
  partitions: Partition[]
  slots: Slot[]
  regions: Region[]
  resources: Record<string, number>
  states: Record<string, string>
  glossary: Record<string, string>
}

/** Import choice for one source partition. `copy` only applies to an id conflict. */
export type PartitionAction = 'skip' | 'add' | 'replace' | 'copy'

export interface ImportPlan { recipe: Recipe; notes: string[] }

const ID = /^[a-z0-9][a-z0-9-]*$/
const PLACEHOLDER = /\{([a-z0-9][a-z0-9-]*)\}/g

type Owner = { when?: Condition | null; effects?: Effects; weight_mods?: WeightMod[] }

function placeholders(text: string | undefined): string[] {
  return [...(text ?? '').matchAll(PLACEHOLDER)].map(match => match[1])
}

function walkCondition(condition: Condition | null | undefined, visit: (leaf: Condition) => void): void {
  if (!condition) return
  if ('all' in condition) condition.all.forEach(child => walkCondition(child, visit))
  else if ('any' in condition) condition.any.forEach(child => walkCondition(child, visit))
  else if ('not' in condition) walkCondition(condition.not, visit)
  else visit(condition)
}

function ownersOf(part: Partition): Owner[] {
  return [part, ...part.options]
}

function conditionsOf(owner: Owner): Array<Condition | null | undefined> {
  return [owner.when, ...(owner.weight_mods ?? []).map(mod => mod.when)]
}

function stateKeys(recipe: Recipe): Set<string> {
  const keys = new Set<string>()
  for (const part of recipe.partitions) for (const option of part.options) {
    Object.keys(option.effects?.set ?? {}).forEach(key => keys.add(key))
    Object.values(option.slots ?? {}).forEach(use => { if (use.set_state) keys.add(use.set_state) })
  }
  return keys
}

// ------------------------------------------------------------------ export

/** Bundle the given partitions (in draw order) with everything they need. */
export function exportPartitions(recipe: Recipe, ids: readonly string[]): PartitionBundle {
  const wanted = new Set(ids)
  const order = [...recipe.draw_order, ...recipe.partitions.map(part => part.id)]
  const partitions = [...new Set(order)].filter(id => wanted.has(id))
    .map(id => recipe.partitions.find(part => part.id === id)).filter((part): part is Partition => Boolean(part)).map(clone)
  const slotIds = new Set<string>()
  const regionIds = new Set<string>()
  const resources: Record<string, number> = {}
  const stateIds = new Set<string>()
  const tags = new Set<string>()
  for (const part of partitions) {
    part.needs?.forEach(id => regionIds.add(id))
    for (const owner of ownersOf(part)) {
      for (const condition of conditionsOf(owner)) walkCondition(condition, leaf => {
        if ('visible' in leaf) regionIds.add(leaf.visible)
        if ('state' in leaf) stateIds.add(leaf.state)
      })
    }
    for (const option of part.options) {
      option.needs?.forEach(id => regionIds.add(id))
      option.effects?.hide?.forEach(id => regionIds.add(id))
      Object.keys(option.effects?.set ?? {}).forEach(id => stateIds.add(id))
      for (const id of Object.keys(option.effects?.consume ?? {})) {
        if (recipe.resources?.[id] !== undefined) resources[id] = recipe.resources[id]
      }
      placeholders(option.tags).forEach(id => slotIds.add(id))
      Object.keys(option.slots ?? {}).forEach(id => slotIds.add(id))
      for (const use of Object.values(option.slots ?? {})) {
        if (use.set_state) stateIds.add(use.set_state)
        if (use.exclude_state) stateIds.add(use.exclude_state)
      }
      for (const tag of [option.tags ?? '', ...(option.effects?.content_add ?? []), ...(option.effects?.remove_tags ?? []), ...(option.effects?.style_add ?? []), ...(option.effects?.style_remove ?? [])]) {
        tag.split(/[,，\r\n]+/).map(item => item.trim()).filter(Boolean).forEach(item => tags.add(item))
      }
    }
  }
  const slots = (recipe.slots ?? []).filter(slot => slotIds.has(slot.id)).map(clone)
  for (const slot of slots) for (const value of slot.values) tags.add(value.tag)
  // Keep each region's ancestors so the hierarchy survives in an empty recipe.
  const regions = recipe.regions ?? []
  const byId = new Map(regions.map(region => [region.id, region]))
  for (const id of [...regionIds]) {
    for (let cursor = byId.get(id)?.parent; cursor && !regionIds.has(cursor); cursor = byId.get(cursor)?.parent) regionIds.add(cursor)
  }
  const states: Record<string, string> = {}
  for (const id of stateIds) states[id] = recipe.states?.[id] ?? ''
  const glossary: Record<string, string> = {}
  for (const [tag, zh] of Object.entries(recipe.glossary ?? {})) if (tags.has(tag)) glossary[tag] = zh
  return {
    format: PARTITION_BUNDLE_FORMAT, version: 1, partitions, slots,
    regions: regions.filter(region => regionIds.has(region.id)).map(clone),
    resources, states, glossary,
  }
}

// ------------------------------------------------------------------ parsing

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Accept a partition bundle, an exported recipe file `{name, recipe}` or a bare recipe:
 * partitions can be picked out of any of them.
 */
export function parsePartitionSource(raw: string): PartitionBundle {
  let parsed: unknown
  try { parsed = JSON.parse(raw) } catch { throw new Error('无法解析 JSON。') }
  if (isRecord(parsed) && parsed.format === PARTITION_BUNDLE_FORMAT) {
    if (parsed.version !== 1) throw new Error('不支持的分区文件版本。')
    if (!Array.isArray(parsed.partitions)) throw new Error('分区文件缺少 partitions。')
    return checkPartitions({
      format: PARTITION_BUNDLE_FORMAT, version: 1,
      partitions: parsed.partitions as Partition[],
      slots: Array.isArray(parsed.slots) ? parsed.slots as Slot[] : [],
      regions: Array.isArray(parsed.regions) ? parsed.regions as Region[] : [],
      resources: isRecord(parsed.resources) ? parsed.resources as Record<string, number> : {},
      states: isRecord(parsed.states) ? parsed.states as Record<string, string> : {},
      glossary: isRecord(parsed.glossary) ? parsed.glossary as Record<string, string> : {},
    })
  }
  const recipe = isRecord(parsed) && isRecord(parsed.recipe) ? parsed.recipe : parsed
  if (isRecord(recipe) && Array.isArray(recipe.partitions) && Array.isArray(recipe.draw_order)) {
    const source = recipe as unknown as Recipe
    return checkPartitions(exportPartitions(source, source.partitions.map(part => part.id)))
  }
  throw new Error('不是分区或配方 JSON：需要 partitions。')
}

function checkPartitions(bundle: PartitionBundle): PartitionBundle {
  const seen = new Set<string>()
  for (const part of bundle.partitions) {
    if (!isRecord(part) || typeof part.id !== 'string' || !ID.test(part.id) || !Array.isArray(part.options)) {
      throw new Error('分区格式不正确：每个分区需要 id 和 options。')
    }
    if (seen.has(part.id)) throw new Error(`文件里有重复的分区 id「${part.id}」。`)
    seen.add(part.id)
  }
  if (!bundle.partitions.length) throw new Error('文件里没有分区。')
  return bundle
}

// ------------------------------------------------------------------ import

function freeId(base: string, taken: Set<string>): string {
  for (let index = 2; ; index += 1) {
    const suffix = `-${index}`
    const id = `${base.slice(0, 64 - suffix.length).replace(/-+$/, '') || 'x'}${suffix}`
    if (!taken.has(id)) return id
  }
}

function renamePartitionRefs(part: Partition, rename: Map<string, string>): void {
  const mapRef = (ref: string) => {
    const [partition, ...rest] = ref.split('.')
    const next = rename.get(partition)
    return next ? [next, ...rest].join('.') : ref
  }
  for (const owner of ownersOf(part)) {
    for (const condition of conditionsOf(owner)) walkCondition(condition, leaf => {
      if ('chosen' in leaf) (leaf as { chosen: string }).chosen = mapRef(leaf.chosen)
      if ('partition_drawn' in leaf) (leaf as { partition_drawn: string }).partition_drawn = rename.get(leaf.partition_drawn) ?? leaf.partition_drawn
    })
    const effects = owner.effects
    if (!effects) continue
    if (effects.remove_partitions) effects.remove_partitions = effects.remove_partitions.map(id => rename.get(id) ?? id)
    if (effects.remove_options) effects.remove_options = effects.remove_options.map(mapRef)
    if (effects.allow_options) effects.allow_options = Object.fromEntries(Object.entries(effects.allow_options).map(([id, list]) => [rename.get(id) ?? id, list]))
    if (effects.allow_values) effects.allow_values = Object.fromEntries(Object.entries(effects.allow_values).map(([key, list]) => [mapRef(key), list]))
  }
}

function renameSlot(part: Partition, from: string, to: string): void {
  for (const option of part.options) {
    if (option.tags) option.tags = option.tags.replaceAll(`{${from}}`, `{${to}}`)
    if (option.label) option.label = option.label.replaceAll(`{${from}}`, `{${to}}`)
    if (option.slots?.[from]) { option.slots[to] = option.slots[from]; delete option.slots[from] }
  }
}

function renameSlotInAllowValues(recipe: Recipe, imported: Set<string>, slotRename: Map<string, Map<string, string>>): void {
  // allow_values keys are `partition.option.slot`; follow renamed slots of imported partitions.
  for (const part of recipe.partitions) for (const owner of ownersOf(part)) {
    const values = owner.effects?.allow_values
    if (!values) continue
    owner.effects!.allow_values = Object.fromEntries(Object.entries(values).map(([key, list]) => {
      const [partition, option, slot] = key.split('.')
      const next = imported.has(partition) ? slotRename.get(partition)?.get(slot) : undefined
      return [next ? `${partition}.${option}.${next}` : key, list]
    }))
  }
}

/** Same values (id, tag, weight); labels and key order do not matter. */
function sameSlot(a: Slot, b: Slot): boolean {
  const values = (slot: Slot) => slot.values.map(value => `${value.id}\u0000${value.tag}\u0000${value.weight ?? 1}`).sort().join('\u0001')
  return values(a) === values(b)
}

/** Build the merged recipe for the chosen actions without touching `target`. */
export function planPartitionImport(target: Recipe, bundle: PartitionBundle, actions: Record<string, PartitionAction>): ImportPlan {
  const recipe = clone(target)
  const notes: string[] = []
  const chosen = bundle.partitions.filter(part => (actions[part.id] ?? 'skip') !== 'skip').map(clone)
  if (!chosen.length) return { recipe, notes }
  const existing = new Set(recipe.partitions.map(part => part.id))
  const taken = new Set([...existing, ...bundle.partitions.map(part => part.id)])
  const rename = new Map<string, string>()
  const replacing = new Set<string>()
  for (const part of chosen) {
    const action = actions[part.id]
    if (!existing.has(part.id)) continue
    if (action === 'replace') replacing.add(part.id)
    else {
      const id = freeId(part.id, taken)
      taken.add(id)
      rename.set(part.id, id)
    }
  }
  for (const part of chosen) {
    renamePartitionRefs(part, rename)
    part.id = rename.get(part.id) ?? part.id
  }
  const importedIds = new Set(chosen.map(part => part.id))

  // Recipe-level definitions: add what is missing, never overwrite the target's.
  const slotRename = new Map<string, Map<string, string>>()
  const slots = recipe.slots ?? (recipe.slots = [])
  const slotTaken = new Set(slots.map(slot => slot.id))
  for (const slot of bundle.slots) {
    const users = chosen.filter(part => part.options.some(option => placeholders(option.tags).includes(slot.id) || option.slots?.[slot.id]))
    if (!users.length) continue
    const current = slots.find(item => item.id === slot.id)
    if (current && sameSlot(current, slot)) continue
    let id = slot.id
    if (current) {
      id = freeId(slot.id, slotTaken)
      notes.push(`取值槽「${slot.label || slot.id}」与当前配方的同名槽内容不同，已作为「${id}」添加。`)
      for (const part of users) {
        renameSlot(part, slot.id, id)
        if (!slotRename.has(part.id)) slotRename.set(part.id, new Map())
        slotRename.get(part.id)!.set(slot.id, id)
      }
    }
    slotTaken.add(id)
    slots.push({ ...clone(slot), id })
  }
  const regions = recipe.regions ?? (recipe.regions = [])
  const regionIds = new Set(regions.map(region => region.id))
  const bundleRegions = new Set(bundle.regions.map(region => region.id))
  for (const region of bundle.regions) {
    if (regionIds.has(region.id)) continue
    const parent = region.parent && (regionIds.has(region.parent) || bundleRegions.has(region.parent)) ? region.parent : null
    regions.push({ ...clone(region), parent })
    regionIds.add(region.id)
  }
  const resources = recipe.resources ?? (recipe.resources = {})
  for (const [id, amount] of Object.entries(bundle.resources)) if (resources[id] === undefined) resources[id] = amount
  const states = recipe.states ?? (recipe.states = {})
  for (const [id, label] of Object.entries(bundle.states)) if (states[id] === undefined && label) states[id] = label
  const glossary = recipe.glossary ?? (recipe.glossary = {})
  for (const [tag, zh] of Object.entries(bundle.glossary)) if (glossary[tag] === undefined) glossary[tag] = zh

  // Replaced partitions keep their position; options dropped by the new version lose
  // their references elsewhere, exactly like deleting those options.
  for (const part of chosen) {
    const index = recipe.partitions.findIndex(item => item.id === part.id)
    if (replacing.has(part.id) && index >= 0) {
      const old = recipe.partitions[index]
      recipe.partitions[index] = part
      // Swap first so the old version's own references disappear with it.
      const kept = new Set(part.options.map(option => option.id))
      for (const option of old.options) {
        if (kept.has(option.id)) continue
        for (const reference of findReferences(recipe, old.id, option.id)) {
          notes.push(`${reference.where}的${reference.text}引用了被替换掉的选项「${old.label || old.id}.${option.label || option.id}」，已删除。`)
          reference.remove(recipe)
        }
      }
    } else {
      recipe.partitions.push(part)
      recipe.draw_order.push(part.id)
      if (recipe.prompt_order) recipe.prompt_order.push(part.id)
    }
  }
  renameSlotInAllowValues(recipe, importedIds, slotRename)
  for (const part of recipe.partitions) if (importedIds.has(part.id)) pruneDangling(recipe, part, notes)
  return { recipe, notes }
}

/** Remove references from an imported partition that the merged recipe cannot satisfy. */
function pruneDangling(recipe: Recipe, part: Partition, notes: string[]): void {
  const parts = new Map(recipe.partitions.map(item => [item.id, item]))
  const regions = new Set((recipe.regions ?? []).map(region => region.id))
  const states = stateKeys(recipe)
  const slots = new Map((recipe.slots ?? []).map(slot => [slot.id, slot]))
  const hasOption = (ref: string) => {
    const [partition, option] = ref.split('.')
    return Boolean(parts.get(partition)?.options.some(item => item.id === option))
  }
  const describe = (leaf: Condition) => 'chosen' in leaf ? `已选 ${leaf.chosen}`
    : 'partition_drawn' in leaf ? `${leaf.partition_drawn} 有结果`
      : 'state' in leaf ? `状态 ${leaf.state}` : 'visible' in leaf ? `${leaf.visible} 可见` : ''
  const dangling = (leaf: Condition) => ('chosen' in leaf && !hasOption(leaf.chosen))
    || ('partition_drawn' in leaf && !parts.has(leaf.partition_drawn))
    || ('state' in leaf && !states.has(leaf.state))
    || ('visible' in leaf && !regions.has(leaf.visible))
  const label = part.label || part.id
  const prune = (condition: Condition | null | undefined, where: string): Condition | null => {
    const broken: string[] = []
    walkCondition(condition, leaf => { if (dangling(leaf)) broken.push(describe(leaf)) })
    if (!broken.length) return condition ?? null
    notes.push(`${where}的条件「${broken.join('、')}」在当前配方中不存在，已删除。`)
    return pruneLeaves(condition, dangling)
  }
  part.when = prune(part.when, `分区「${label}」`)
  part.needs = part.needs?.filter(id => regions.has(id))
  for (const option of part.options) {
    const where = `选项「${label}.${option.label || option.id}」`
    if (option.when) option.when = prune(option.when, where)
    if (option.weight_mods?.length) {
      // A weight multiplier with a missing reference is dropped as a whole.
      option.weight_mods = option.weight_mods.filter(mod => {
        const broken: string[] = []
        walkCondition(mod.when, leaf => { if (dangling(leaf)) broken.push(describe(leaf)) })
        if (broken.length) notes.push(`${where}的条件权重（×${mod.factor}）引用「${broken.join('、')}」在当前配方中不存在，已删除。`)
        return !broken.length
      })
    }
    for (const use of Object.values(option.slots ?? {})) {
      if (use.exclude_state && !states.has(use.exclude_state)) {
        notes.push(`${where}的取值排除状态「${use.exclude_state}」在当前配方中不存在，已删除。`)
        use.exclude_state = null
      }
    }
    const effects = option.effects
    if (!effects) continue
    const removedParts = (effects.remove_partitions ?? []).filter(id => !parts.has(id) || id === part.id)
    if (removedParts.length) {
      notes.push(`${where}的「移除分区」${removedParts.join('、')} 不存在，已删除。`)
      effects.remove_partitions = effects.remove_partitions!.filter(id => !removedParts.includes(id))
    }
    const removedOptions = (effects.remove_options ?? []).filter(ref => !hasOption(ref) || ref.split('.')[0] === part.id)
    if (removedOptions.length) {
      notes.push(`${where}的「移除选项」${removedOptions.join('、')} 不存在，已删除。`)
      effects.remove_options = effects.remove_options!.filter(ref => !removedOptions.includes(ref))
    }
    for (const [id, list] of Object.entries(effects.allow_options ?? {})) {
      const known = new Set(parts.get(id)?.options.map(item => item.id) ?? [])
      const next = id === part.id ? [] : list.filter(item => known.has(item))
      if (next.length === list.length) continue
      notes.push(`${where}的「只允许选项」${id} 中有 ${list.length - next.length} 项不存在，已删除${next.length ? '' : '整条限制'}。`)
      if (next.length) effects.allow_options![id] = next
      else delete effects.allow_options![id]
    }
    for (const [key, list] of Object.entries(effects.allow_values ?? {})) {
      const [partition, optionId, slotId] = key.split('.')
      const owner = parts.get(partition)?.options.find(item => item.id === optionId)
      const slot = slots.get(slotId)
      const usable = partition !== part.id && owner && slot && placeholders(owner.tags).includes(slotId)
      const known = new Set(slot?.values.map(value => value.id) ?? [])
      const next = usable ? list.filter(id => known.has(id)) : []
      if (next.length === list.length) continue
      notes.push(`${where}的「只允许取值」${key} 中有 ${list.length - next.length} 项不存在，已删除${next.length ? '' : '整条限制'}。`)
      if (next.length) effects.allow_values![key] = next
      else delete effects.allow_values![key]
    }
    if (effects.hide) effects.hide = effects.hide.filter(id => regions.has(id))
  }
}

function pruneLeaves(condition: Condition | null | undefined, target: (leaf: Condition) => boolean): Condition | null {
  if (!condition) return null
  if ('all' in condition || 'any' in condition) {
    const list = 'all' in condition ? condition.all : condition.any
    const children = list.map(child => pruneLeaves(child, target)).filter((child): child is Condition => child !== null)
    if (!children.length) return null
    if (children.length === 1) return children[0]
    return 'all' in condition ? { all: children } : { any: children }
  }
  if ('not' in condition) {
    const inner = pruneLeaves(condition.not, target)
    return inner ? { not: inner } : null
  }
  return target(condition) ? null : condition
}

/** Partitions in the target that share an id with the bundle (need replace/copy). */
export function conflictingPartitions(target: Recipe, bundle: PartitionBundle): Set<string> {
  const ids = new Set(target.partitions.map(part => part.id))
  return new Set(bundle.partitions.filter(part => ids.has(part.id)).map(part => part.id))
}

export function bundleFileName(recipeName: string, bundle: PartitionBundle): string {
  // eslint-disable-next-line no-control-regex
  const base = (recipeName || 'recipe').replace(/[\u0000-\u001f\u007f\\/:*?"<>|]+/g, '_').trim().slice(0, 60) || 'recipe'
  const what = bundle.partitions.length === 1 ? bundle.partitions[0].id : String(bundle.partitions.length)
  return `${base}.${what}.partitions.json`
}

