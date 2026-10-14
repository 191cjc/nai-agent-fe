interface SourceRange {
  start: number
  end: number
}

interface NumericGroup extends SourceRange {
  prefixEnd: number
  weight: string
  closed: boolean
}

interface Scope {
  close: string
  numeric?: NumericGroup
}

export interface PromptTag extends SourceRange {
  source: string
  text: string
  weight: string | null
  weightRange: SourceRange | null
}

const NUMBER_PREFIX = /^[+-]?(?:\d+(?:\.\d+)?|\.\d+)::/
const BRACKETS: Record<string, string> = { '(': ')', '[': ']', '{': '}' }

function numericPrefix(source: string, index: number): string | null {
  if (index > 0 && !/[\s,()[\]{}:]/.test(source[index - 1])) return null
  return NUMBER_PREFIX.exec(source.slice(index))?.[0] ?? null
}

function escaped(source: string, index: number): boolean {
  let slashes = 0
  for (let previous = index - 1; previous >= 0 && source[previous] === '\\'; previous -= 1) slashes += 1
  return slashes % 2 === 1
}

function trimRange(source: string, start: number, end: number): SourceRange {
  while (start < end && /\s/.test(source[start])) start += 1
  while (end > start && /\s/.test(source[end - 1]) && !escaped(source, end - 1)) end -= 1
  return { start, end }
}

// Keep decimal arithmetic exact even for manually entered weights with extra
// precision or large integer parts. No floating-point rounding or weight cap.
function decimalParts(value: string): { units: bigint; places: number } {
  const negative = value.startsWith('-')
  const unsigned = value.replace(/^[+-]/, '')
  const [whole, fraction = ''] = unsigned.split('.')
  const places = Math.max(1, fraction.length)
  const units = BigInt(`${whole || '0'}${fraction.padEnd(places, '0')}`)
  return { units: negative ? -units : units, places }
}

function formatDecimal(units: bigint, places: number): string {
  const negative = units < 0n
  const digits = (negative ? -units : units).toString().padStart(places + 1, '0')
  const whole = digits.slice(0, -places)
  const fraction = digits.slice(-places).replace(/0+$/, '') || '0'
  return `${negative ? '-' : ''}${whole}.${fraction}`
}

function normalizedWeight(value: string): string {
  const { units, places } = decimalParts(value)
  return formatDecimal(units, places)
}

/**
 * Commas/newlines split tags only outside escaped or balanced scopes. Ranges
 * refer to the original string: viewing tags must never rewrite a prompt.
 * Unknown/incomplete emphasis stays visible but is not guessed or converted.
 */
export function parsePromptTags(source: string): PromptTag[] {
  const tags: PromptTag[] = []
  const scopes: Scope[] = []
  let groups: NumericGroup[] = []
  let start = 0
  let unsafe = false
  let legacyEmphasis = false

  function finish(end: number) {
    const range = trimRange(source, start, end)
    if (range.start < range.end) {
      const raw = source.slice(range.start, range.end)
      const outer = groups.find(group => group.start === range.start && group.end === range.end && group.closed)
      if (!unsafe && scopes.length === 0 && outer && source.slice(outer.prefixEnd, outer.end - 2).trim()) {
        tags.push({
          ...range,
          source: raw,
          text: source.slice(outer.prefixEnd, outer.end - 2),
          weight: normalizedWeight(outer.weight),
          weightRange: { start: outer.start, end: outer.prefixEnd - 2 },
        })
      } else {
        // Appending a closing :: to a literal trailing : would produce :::,
        // where the delimiter could consume part of the original tag text.
        const trailingColon = raw.endsWith(':') && !escaped(source, range.end - 1)
        tags.push({
          ...range,
          source: raw,
          text: raw,
          weight: !unsafe && scopes.length === 0 && groups.length === 0 && !legacyEmphasis && !trailingColon ? '1.0' : null,
          weightRange: null,
        })
      }
    }
    start = end + 1
    groups = []
    unsafe = false
    legacyEmphasis = false
  }

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index]
    if (character === '\\') {
      if (index + 1 === source.length) unsafe = true
      index += 1
      continue
    }
    const prefix = numericPrefix(source, index)
    if (prefix) {
      const numeric = { start: index, prefixEnd: index + prefix.length, end: -1, weight: prefix.slice(0, -2), closed: false }
      groups.push(numeric)
      scopes.push({ close: '::', numeric })
      index += prefix.length - 1
      continue
    }
    if (source.startsWith('::', index)) {
      const scope = scopes.at(-1)
      if (scope?.close === '::') {
        scopes.pop()
        if (scope.numeric) {
          scope.numeric.end = index + 2
          scope.numeric.closed = true
        }
      } else {
        // Protect possible unknown emphasis scopes from comma splitting.
        scopes.push({ close: '::' })
        unsafe = true
      }
      index += 1
      continue
    }
    if (BRACKETS[character]) {
      scopes.push({ close: BRACKETS[character] })
      if (character === '{' || character === '[') legacyEmphasis = true
    } else if (')]}'.includes(character)) {
      if (scopes.at(-1)?.close === character) scopes.pop()
      else unsafe = true
    } else if ((character === ',' || character === '\n' || character === '\r') && scopes.length === 0) {
      finish(index)
    }
  }
  finish(source.length)
  return tags
}

/** Replace only the selected source span, preserving every other character. */
export function adjustPromptTagWeight(source: string, tag: PromptTag, direction: -1 | 1): string | null {
  if (tag.weight === null || source.slice(tag.start, tag.end) !== tag.source) return null
  const { units, places } = decimalParts(tag.weight)
  const nextWeight = formatDecimal(units + BigInt(direction) * 10n ** BigInt(places - 1), places)
  if (tag.weightRange) {
    return source.slice(0, tag.weightRange.start) + nextWeight + source.slice(tag.weightRange.end)
  }
  return source.slice(0, tag.start) + `${nextWeight}::${tag.source}::` + source.slice(tag.end)
}
