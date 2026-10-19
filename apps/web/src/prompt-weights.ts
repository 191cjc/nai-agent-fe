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
  hidden?: boolean
  manualOnly?: boolean
  blockStart?: number
  blockEnd?: number
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
export function decimalParts(value: string): { units: bigint; places: number } {
  if (!/^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(value)) throw new Error('权重须为普通十进制数，不支持科学计数法。')
  const negative = value.startsWith('-')
  const unsigned = value.replace(/^[+-]/, '')
  const [whole, fraction = ''] = unsigned.split('.')
  const places = Math.max(1, fraction.length)
  const units = BigInt(`${whole || '0'}${fraction.padEnd(places, '0')}`)
  return { units: negative ? -units : units, places }
}

export function formatDecimal(units: bigint, places: number): string {
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
function parseLegacyPromptTags(source: string): PromptTag[] {
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

interface PromptLine extends SourceRange { bodyStart: number; hidden: boolean }

function promptLines(source: string): PromptLine[] {
  const lines: PromptLine[] = []
  const pattern = /([^\r\n]*)(\r\n|\r|\n|$)/g
  for (const match of source.matchAll(pattern)) {
    if (!match[0]) continue
    const start = match.index
    const prefix = /^[ \t]*\/\/ ?/.exec(match[1])
    lines.push({ start, end: start + match[0].length,
      bodyStart: start + (prefix?.[0].length ?? 0), hidden: prefix !== null })
  }
  return lines
}

/** Whole physical line comments are editor syntax; surviving text stays literal. */
export function compilePromptComments(source: string): string {
  return promptLines(source).filter(line => !line.hidden).map(line => source.slice(line.start, line.end)).join('')
}

/** Start appended content on a fresh line, even after a hidden final tag. */
export function appendPromptText(current: string, text: string): string {
  return [current, text].filter(part => part.trim()).join(',\n')
}

/**
 * Hidden occurrences share the same index space as active occurrences. Mapping
 * uses raw source offsets, never offsets from the decommented virtual source.
 * A scope crossing active/comment blocks is conservatively one manual entry.
 */
export function parsePromptTags(source: string, comments = false): PromptTag[] {
  const legacy = parseLegacyPromptTags(source)
  if (!comments) return legacy
  const lines = promptLines(source)
  const manualField = (): PromptTag[] => {
    const range = trimRange(source, 0, source.length)
    const raw = source.slice(range.start, range.end)
    return raw ? [{ ...range, source: raw, text: raw, weight: null, weightRange: null, hidden: false, manualOnly: true }] : []
  }
  const crossesModes = legacy.some(tag => /[\r\n]/.test(tag.source)
    && new Set(lines.filter(line => line.start < tag.end && line.end > tag.start).map(line => line.hidden)).size > 1)
  if (crossesModes) return manualField()
  const tags: PromptTag[] = []
  for (let index = 0; index < lines.length;) {
    const first = index
    const hidden = lines[index].hidden
    while (index < lines.length && lines[index].hidden === hidden) index += 1
    const block = lines.slice(first, index)
    let virtual = ''
    const offsets: number[] = []
    for (const line of block) {
      const start = hidden ? line.bodyStart : line.start
      for (let position = start; position < line.end; position += 1) {
        offsets.push(position)
        virtual += source[position]
      }
    }
    for (const tag of parseLegacyPromptTags(virtual)) {
      const start = offsets[tag.start]
      const end = offsets[tag.end - 1] + 1
      // Moving a literal inline // onto its own line would turn it into a
      // comment. A doubled hidden marker likewise cannot be restored safely.
      const manualOnly = /[\r\n]/.test(tag.source) || /^[ \t]*\/\//.test(tag.source)
      tags.push({ ...tag, start, end, source: source.slice(start, end),
        weight: manualOnly ? null : tag.weight,
        weightRange: !hidden && !manualOnly && tag.weightRange
          ? { start: offsets[tag.weightRange.start], end: offsets[tag.weightRange.end - 1] + 1 } : null,
        hidden, manualOnly, blockStart: block[0].start, blockEnd: block.at(-1)!.end })
    }
  }
  // A sibling's zero omission or an outer neutral unwrap could promote an
  // inline literal marker to a comment. Keep its whole context unchanged.
  if (tags.some(tag => !tag.hidden && (/^[ \t]*\/\//.test(tag.source) || /^[ \t]*\/\//.test(tag.text)))) return manualField()
  return tags
}

/** Formatting is explicit on blur; ambiguous multiline source is never reflowed. */
export function formatPromptTags(source: string): string {
  const tags = parsePromptTags(source, true)
  if (tags.some(tag => tag.manualOnly)) return source
  return tags.map(tag => `${tag.hidden ? '// ' : ''}${tag.source}`).join(',\n')
}

/** Reflow before toggling, so one comment cannot accidentally hide a sibling. */
export function togglePromptTagHidden(source: string, tag: PromptTag): string | null {
  const tags = parsePromptTags(source, true)
  const index = tags.findIndex(current => current.start === tag.start && current.end === tag.end && current.source === tag.source)
  if (index < 0 || tags.some(current => current.manualOnly)) return null
  return tags.map((current, position) => `${(position === index ? !current.hidden : current.hidden) ? '// ' : ''}${current.source}`).join(',\n')
}

/** Replace only the selected source span, preserving every other character. */
export function adjustPromptTagWeight(source: string, tag: PromptTag, direction: -1 | 1): string | null {
  if (tag.weight === null || source.slice(tag.start, tag.end) !== tag.source) return null
  const { units, places } = decimalParts(tag.weight)
  const nextWeight = formatDecimal(units + BigInt(direction) * 10n ** BigInt(places - 1), places)
  return setPromptTagWeight(source, tag, nextWeight)
}

/** Set an absolute exact weight without changing the tag body or its siblings. */
export function setPromptTagWeight(source: string, tag: PromptTag, weight: string): string | null {
  if (tag.hidden || tag.manualOnly || tag.weight === null || source.slice(tag.start, tag.end) !== tag.source) return null
  let nextWeight: string
  try {
    nextWeight = normalizedWeight(weight)
  } catch {
    return null
  }
  if (nextWeight === '1.0') {
    return tag.weightRange
      ? source.slice(0, tag.start) + source.slice(tag.weightRange.end + 2, tag.end - 2) + source.slice(tag.end)
      : source
  }
  if (tag.weightRange) {
    return source.slice(0, tag.weightRange.start) + nextWeight + source.slice(tag.weightRange.end)
  }
  return source.slice(0, tag.start) + `${nextWeight}::${tag.source}::` + source.slice(tag.end)
}
