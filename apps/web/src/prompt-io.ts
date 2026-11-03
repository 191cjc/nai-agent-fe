/**
 * Plain-text import/export of training-set prompt libraries.
 *
 *   # 分类：portrait          category marker (known ids only; others → custom)
 *   1girl, solo, portrait, …  one prompt per line
 *   2girls, upper body, …     a multi-person scene …
 *   人物：girl, long hair, …  … followed by one line per person
 *   # anything else           comment
 *
 * `#` never starts a Danbooru tag line and `人物：` is not a tag, so both are
 * unambiguous; NovelAI `|` mixing and `[ ]` emphasis stay usable inside prompts.
 */
import { CUSTOM_CATEGORY, MAX_DATASET_PROMPT_LENGTH, MAX_ITEM_CHARACTERS, nextCustomId, type DatasetEntry } from './dataset-run'

const CATEGORY = /^#\s*分类\s*[:：]\s*(\S+)\s*$/
const PERSON = /^人物\s*[:：]\s*/

export interface ParsedPrompts {
  entries: DatasetEntry[]
  multi: number
}

export function formatPrompts(entries: readonly DatasetEntry[], title: string): string {
  const lines = [
    `# ${title}`,
    '# 每行一条提示词；「人物：」开头的行属于上一条（多人条目的单个人物）；# 开头为注释。',
  ]
  let category = ''
  for (const entry of entries) {
    if (entry.category !== category) {
      category = entry.category
      lines.push('', `# 分类：${category}`)
    }
    lines.push(oneLine(entry.prompt), ...(entry.characters ?? []).map(character => `人物：${oneLine(character)}`))
  }
  return `${lines.join('\n')}\n`
}

/** Parses pasted or file text into new, selected entries with fresh unique ids. */
export function parsePrompts(
  text: string, existing: readonly DatasetEntry[], categories: readonly string[], allowCharacters: boolean,
): ParsedPrompts {
  const known = new Set(categories)
  const entries: DatasetEntry[] = []
  let category = CUSTOM_CATEGORY
  let multi = 0
  text.split(/\r\n|\r|\n/).forEach((raw, index) => {
    const line = raw.trim()
    const where = `第 ${index + 1} 行`
    if (!line) return
    const marker = line.match(CATEGORY)
    if (marker) {
      category = known.has(marker[1]) ? marker[1] : CUSTOM_CATEGORY
      return
    }
    if (line.startsWith('#')) return
    if (line.startsWith('//')) throw new Error(`${where}以 // 开头；训练集提示词不能包含注释行。`)
    const person = line.match(PERSON)
    if (person) {
      const previous = entries.at(-1)
      if (!allowCharacters) throw new Error(`${where}是「人物：」行，角色训练集不支持多人条目。`)
      if (!previous) throw new Error(`${where}的「人物：」前面没有场景提示词。`)
      const prompt = line.slice(person[0].length).trim()
      if (!prompt) throw new Error(`${where}的人物提示词为空。`)
      if (prompt.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${where}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
      const characters = [...(previous.characters ?? []), prompt]
      if (characters.length > MAX_ITEM_CHARACTERS) throw new Error(`${where}：一条提示词最多 ${MAX_ITEM_CHARACTERS} 个人物。`)
      if (!previous.characters?.length) multi += 1
      entries[entries.length - 1] = { ...previous, characters }
      return
    }
    if (line.length > MAX_DATASET_PROMPT_LENGTH) throw new Error(`${where}超过 ${MAX_DATASET_PROMPT_LENGTH} 字符。`)
    entries.push({ id: nextCustomId([...existing, ...entries]), category, prompt: line, selected: true })
  })
  if (!entries.length) throw new Error('没有找到提示词：每行写一条，# 开头的行会被忽略。')
  return { entries, multi }
}

function oneLine(text: string): string {
  return text.replace(/\s*[\r\n]+\s*/g, ', ').trim()
}

export function downloadText(text: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
  const link = document.createElement('a')
  try {
    link.href = url
    link.download = filename
    document.body.append(link)
    link.click()
  } finally {
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }
}
