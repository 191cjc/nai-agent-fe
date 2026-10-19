import { compilePromptComments, decimalParts, formatDecimal, parsePromptTags, setPromptTagWeight, type PromptTag } from './prompt-weights'

export interface StyleExperimentRange {
  tagIndex: number
  min: string
  max: string
  step: string
}

export interface StyleExperimentWeight {
  tagIndex: number
  label: string
  weight: string
}

export interface StyleExperimentCombination {
  stylePrompt: string
  weights: StyleExperimentWeight[]
}

export interface StyleExperimentDimension extends StyleExperimentRange {
  readonly label: string
  readonly count: bigint
  readonly tag: PromptTag
  readonly minUnits: bigint
  readonly stepUnits: bigint
  readonly places: number
}

export interface StyleExperimentPlan {
  readonly source: string
  readonly dimensions: readonly StyleExperimentDimension[]
  readonly total: bigint
  /** Conservative upper bound; never materialize a range to find its length. */
  readonly maxStyleLength: number
  readonly maxEffectiveStyleLength: number
  readonly canBeEmpty: boolean
  readonly comments: boolean
}

interface SourceRange { start: number; end: number }

function legacyOmissionRanges(source: string, tags: PromptTag[], omitted: Set<number>): SourceRange[] {
  if (!omitted.size) return []
  if (omitted.size === tags.length) return [{ start: 0, end: source.length }]
  const ranges: SourceRange[] = []
  for (let index = 0; index < tags.length; index += 1) {
    if (!omitted.has(index)) continue
    const first = index
    while (omitted.has(index + 1)) index += 1
    ranges.push(index + 1 < tags.length
      ? { start: tags[first].start, end: tags[index + 1].start }
      : { start: tags[first - 1].end, end: tags[index].end })
  }
  return ranges
}

function omissionRanges(source: string, tags: PromptTag[], omitted: Set<number>, comments: boolean): SourceRange[] {
  if (!comments) return legacyOmissionRanges(source, tags, omitted)
  const blocks = new Map<number, { end: number; indexes: number[] }>()
  tags.forEach((tag, index) => {
    if (tag.hidden || tag.blockStart === undefined || tag.blockEnd === undefined) return
    const block = blocks.get(tag.blockStart) ?? { end: tag.blockEnd, indexes: [] }
    block.indexes.push(index)
    blocks.set(tag.blockStart, block)
  })
  return [...blocks].flatMap(([start, block]) => {
    const localTags = block.indexes.map(index => ({ ...tags[index], start: tags[index].start - start, end: tags[index].end - start }))
    const localOmitted = new Set(block.indexes.flatMap((index, local) => omitted.has(index) ? [local] : []))
    return legacyOmissionRanges(source.slice(start, block.end), localTags, localOmitted)
      .map(range => ({ start: start + range.start, end: start + range.end }))
  })
}

export function createStyleExperimentPlan(source: string, ranges: StyleExperimentRange[], comments = true): StyleExperimentPlan {
  if (!ranges.length) throw new Error('请至少选择一个画风词条。')
  const tags = parsePromptTags(source, comments)
  const selected = new Set<number>()
  const dimensions = ranges.map(range => {
    const tag = tags[range.tagIndex]
    if (!Number.isInteger(range.tagIndex) || !tag || tag.hidden || tag.manualOnly || tag.weight === null || selected.has(range.tagIndex)) {
      throw new Error('画风词条已变化或不支持数值权重，请重新选择。')
    }
    selected.add(range.tagIndex)
    const values = [range.min, range.max, range.step].map(value => {
      const parsed = decimalParts(value.trim())
      return decimalParts(formatDecimal(parsed.units, parsed.places))
    })
    const countPlaces = Math.max(...values.map(value => value.places))
    const [countMin, countMax, countStep] = values.map(value => value.units * 10n ** BigInt(countPlaces - value.places))
    const places = Math.max(values[0].places, values[2].places)
    const minUnits = values[0].units * 10n ** BigInt(places - values[0].places)
    const stepUnits = values[2].units * 10n ** BigInt(places - values[2].places)
    if (stepUnits <= 0n) throw new Error('画风权重步长须大于 0。')
    if (countMin > countMax) throw new Error('画风权重下限不能大于上限。')
    const count = (countMax - countMin) / countStep + 1n
    // Remove insignificant input zeros before bounding rendered weight length.
    // The common scale still preserves every exact min + n * step value.
    return Object.freeze({
      tagIndex: range.tagIndex, label: tag.text, tag: Object.freeze(tag),
      min: formatDecimal(minUnits, places), max: formatDecimal(values[1].units, values[1].places),
      step: formatDecimal(stepUnits, places), count, minUnits, stepUnits, places,
    })
  }).sort((left, right) => left.tag.start - right.tag.start)
  const fixedZeros = new Set(dimensions.filter(dimension => dimension.count === 1n && dimension.minUnits === 0n)
    .map(dimension => dimension.tagIndex))
  let total = 1n
  const fixedOmissions = omissionRanges(source, tags, fixedZeros, comments)
  let fixedSource = source
  for (const range of [...fixedOmissions].sort((left, right) => right.start - left.start)) {
    fixedSource = fixedSource.slice(0, range.start) + fixedSource.slice(range.end)
  }
  let maxStyleLength = fixedSource.length
  let growth = 0
  for (const dimension of dimensions) {
    total *= dimension.count
    if (fixedZeros.has(dimension.tagIndex)) continue
    // A single neutral grid point removes any outer numeric wrapper, even
    // when the configured maximum is above 1 but is not reached by the step.
    if (dimension.count === 1n && dimension.min === '1.0') {
      growth += dimension.tag.text.length - dimension.tag.source.length
      continue
    }
    const last = dimension.minUnits + (dimension.count - 1n) * dimension.stepUnits
    const absolute = (value: bigint) => value < 0n ? -value : value
    const largest = absolute(dimension.minUnits) > absolute(last) ? absolute(dimension.minUnits) : absolute(last)
    const integerDigits = (largest / 10n ** BigInt(dimension.places)).toString().length
    const maxWeightLength = integerDigits + 1 + dimension.places + (dimension.minUnits < 0n ? 1 : 0)
    growth += dimension.tag.weightRange
      ? maxWeightLength - (dimension.tag.weightRange.end - dimension.tag.weightRange.start)
      : maxWeightLength + 4
  }
  maxStyleLength += growth
  const maxEffectiveStyleLength = comments ? compilePromptComments(fixedSource).length + growth
    : maxStyleLength ? maxStyleLength - (source.length - source.trim().length) : 0
  const canBeEmpty = dimensions.length === tags.filter(tag => !tag.hidden).length && dimensions.every(dimension =>
    dimension.minUnits <= 0n && -dimension.minUnits % dimension.stepUnits === 0n
    && -dimension.minUnits / dimension.stepUnits < dimension.count)
  return Object.freeze({ source, dimensions: Object.freeze(dimensions), total, maxStyleLength, maxEffectiveStyleLength, canBeEmpty, comments })
}

/** Decode only one mixed-radix ordinal; the last source occurrence varies fastest. */
export function styleExperimentCombination(plan: StyleExperimentPlan, index: bigint): StyleExperimentCombination {
  if (index < 0n || index >= plan.total) throw new Error('画风实验组合序号超出范围。')
  let remaining = index
  let stylePrompt = plan.source
  const weights: StyleExperimentWeight[] = []
  const omitted = new Set<number>()
  const edits: (SourceRange & { tag?: PromptTag; weight?: string })[] = []
  for (let position = plan.dimensions.length - 1; position >= 0; position -= 1) {
    const dimension = plan.dimensions[position]
    const valueIndex = remaining % dimension.count
    remaining /= dimension.count
    const weight = formatDecimal(dimension.minUnits + valueIndex * dimension.stepUnits, dimension.places)
    if (weight === '0.0') omitted.add(dimension.tagIndex)
    else edits.push({ start: dimension.tag.start, end: dimension.tag.end, tag: dimension.tag, weight })
    weights.push({ tagIndex: dimension.tagIndex, label: dimension.label, weight })
  }
  edits.push(...omissionRanges(plan.source, parsePromptTags(plan.source, plan.comments), omitted, plan.comments))
  for (const edit of edits.sort((left, right) => right.start - left.start)) {
    if (edit.tag && edit.weight !== undefined) {
      const updated = setPromptTagWeight(stylePrompt, edit.tag, edit.weight)
      if (updated === null) throw new Error('画风词条源文本不匹配，请重新选择。')
      stylePrompt = updated
    } else stylePrompt = stylePrompt.slice(0, edit.start) + stylePrompt.slice(edit.end)
  }
  return { stylePrompt, weights: weights.reverse() }
}
