import { decimalParts, formatDecimal, parsePromptTags, setPromptTagWeight, type PromptTag } from './prompt-weights'

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
}

export function createStyleExperimentPlan(source: string, ranges: StyleExperimentRange[]): StyleExperimentPlan {
  if (!ranges.length) throw new Error('请至少选择一个画风词条。')
  const tags = parsePromptTags(source)
  const selected = new Set<number>()
  const dimensions = ranges.map(range => {
    const tag = tags[range.tagIndex]
    if (!Number.isInteger(range.tagIndex) || !tag || tag.weight === null || selected.has(range.tagIndex)) {
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
  let total = 1n
  let maxStyleLength = source.length
  for (const dimension of dimensions) {
    total *= dimension.count
    const last = dimension.minUnits + (dimension.count - 1n) * dimension.stepUnits
    const absolute = (value: bigint) => value < 0n ? -value : value
    const largest = absolute(dimension.minUnits) > absolute(last) ? absolute(dimension.minUnits) : absolute(last)
    const integerDigits = (largest / 10n ** BigInt(dimension.places)).toString().length
    const maxWeightLength = integerDigits + 1 + dimension.places + (dimension.minUnits < 0n ? 1 : 0)
    maxStyleLength += dimension.tag.weightRange
      ? maxWeightLength - (dimension.tag.weightRange.end - dimension.tag.weightRange.start)
      : maxWeightLength + 4
  }
  return Object.freeze({ source, dimensions: Object.freeze(dimensions), total, maxStyleLength })
}

/** Decode only one mixed-radix ordinal; the last source occurrence varies fastest. */
export function styleExperimentCombination(plan: StyleExperimentPlan, index: bigint): StyleExperimentCombination {
  if (index < 0n || index >= plan.total) throw new Error('画风实验组合序号超出范围。')
  let remaining = index
  let stylePrompt = plan.source
  const weights: StyleExperimentWeight[] = []
  for (let position = plan.dimensions.length - 1; position >= 0; position -= 1) {
    const dimension = plan.dimensions[position]
    const valueIndex = remaining % dimension.count
    remaining /= dimension.count
    const weight = formatDecimal(dimension.minUnits + valueIndex * dimension.stepUnits, dimension.places)
    const updated = setPromptTagWeight(stylePrompt, dimension.tag, weight)
    if (updated === null) throw new Error('画风词条源文本不匹配，请重新选择。')
    stylePrompt = updated
    weights.push({ tagIndex: dimension.tagIndex, label: dimension.label, weight })
  }
  return { stylePrompt, weights: weights.reverse() }
}
