import { ApiFailure, type GenerationRequest, type GenerationView, type WorkspaceApi } from './api'
import { sanitizedPng } from './png-export'
import { compilePromptComments } from './prompt-weights'

const MAX_ZIP_BYTES = 0xffff_ffff - 64 * 1024 * 1024

let crcTable: Uint32Array | null = null

function crc32(bytes: Uint8Array): number {
  if (!crcTable) {
    crcTable = new Uint32Array(256)
    for (let index = 0; index < 256; index += 1) {
      let value = index
      for (let bit = 0; bit < 8; bit += 1) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1
      crcTable[index] = value >>> 0
    }
  }
  let crc = 0xffffffff
  for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

/** Minimal uncompressed (STORE) zip; PNGs are already compressed. */
class ZipWriter {
  private parts: BlobPart[] = []
  private central: Uint8Array[] = []
  private offset = 0
  private count = 0

  add(name: string, data: Uint8Array): void {
    const encodedName = new TextEncoder().encode(name)
    if (this.offset + data.length + encodedName.length + 30 > MAX_ZIP_BYTES || this.count >= 0xffff) {
      throw new Error('训练集过大，超过单个 zip 的上限；请减少条目或分批导出。')
    }
    const crc = crc32(data)
    const local = new DataView(new ArrayBuffer(30))
    local.setUint32(0, 0x04034b50, true)
    local.setUint16(4, 20, true)
    local.setUint16(6, 0x0800, true)
    local.setUint16(8, 0, true)
    local.setUint16(10, 0, true)
    local.setUint16(12, 0x21, true)
    local.setUint32(14, crc, true)
    local.setUint32(18, data.length, true)
    local.setUint32(22, data.length, true)
    local.setUint16(26, encodedName.length, true)
    local.setUint16(28, 0, true)
    const header = new DataView(new ArrayBuffer(46))
    header.setUint32(0, 0x02014b50, true)
    header.setUint16(4, 20, true)
    header.setUint16(6, 20, true)
    header.setUint16(8, 0x0800, true)
    header.setUint16(10, 0, true)
    header.setUint16(12, 0, true)
    header.setUint16(14, 0x21, true)
    header.setUint32(16, crc, true)
    header.setUint32(20, data.length, true)
    header.setUint32(24, data.length, true)
    header.setUint16(28, encodedName.length, true)
    header.setUint32(42, this.offset, true)
    const centralEntry = new Uint8Array(46 + encodedName.length)
    centralEntry.set(new Uint8Array(header.buffer), 0)
    centralEntry.set(encodedName, 46)
    this.parts.push(local.buffer, encodedName, data)
    this.central.push(centralEntry)
    this.offset += 30 + encodedName.length + data.length
    this.count += 1
  }

  finish(): Blob {
    const size = this.central.reduce((total, entry) => total + entry.length, 0)
    const end = new DataView(new ArrayBuffer(22))
    end.setUint32(0, 0x06054b50, true)
    end.setUint16(8, this.count, true)
    end.setUint16(10, this.count, true)
    end.setUint32(12, size, true)
    end.setUint32(16, this.offset, true)
    return new Blob([...this.parts, ...this.central, end.buffer], { type: 'application/zip' })
  }
}

/** Remove NovelAI emphasis syntax and normalize tag separators for training captions. */
function captionTags(text: string): string[] {
  return text
    .replace(/(^|[\s,([{])[+-]?(?:\d+(?:\.\d+)?|\.\d+)::/g, '$1')
    .replace(/::/g, '')
    .replace(/[{}[\]]/g, '')
    .split(/[,\r\n]+/)
    .map(tag => tag.trim())
    .filter(Boolean)
}

/**
 * Style tags that describe how a character image was drawn. Negative-weighted groups
 * (things the image avoids), artist tags and NovelAI weight syntax are dropped.
 */
export function styleCaptionTags(style: string): string[] {
  const kept = compilePromptComments(style)
    .replace(/(^|[\s,([{])([+-]?(?:\d+(?:\.\d+)?|\.\d+))::([\s\S]*?)::/g,
      (_match, lead: string, weight: string, body: string) => Number(weight) > 0 ? `${lead}${body}` : lead)
  return captionTags(kept).filter(tag => !/^artist:/i.test(tag))
}

/** Animagine XL 4.0 quality tags; captioned so the base model's quality prompt recalls the style. */
export const ANIMAGINE_QUALITY_PREFIX = 'masterpiece, high score, great score, absurdres'

/**
 * Caption order: trigger, optional shared prefix (quality tags), then content tags.
 * The prefix is user text for every image; style and trait tags are never added.
 */
export function datasetCaption(
  parameters: GenerationRequest, trigger: string, prefix = '', includeCharacterStyle = true,
): string {
  const item = parameters.experiment?.kind === 'dataset' ? parameters.experiment.item : undefined
  const compile = parameters.prompt_comments === true && !parameters.prompt_sections
  const sources = item ? [item.prompt] : [
    compile ? compilePromptComments(parameters.positive_prompt) : parameters.positive_prompt,
    ...parameters.character_prompts.map(character => compile ? compilePromptComments(character.prompt) : character.prompt),
  ]
  // Character groups prefix fixed traits before the item; those must bind to the trigger
  // word, so they never appear in captions even if an item repeats one of them.
  const traits = item && parameters.reference
    ? new Set(captionTags(parameters.positive_prompt.trim().slice(0, -item.prompt.trim().length || undefined)))
    : new Set<string>()
  const tags = sources.flatMap(captionTags).filter(tag => !traits.has(tag))
  const lead = [trigger.trim(), ...captionTags(prefix)].filter(Boolean)
  // Character groups vary the drawing style on purpose (style pool); naming it keeps
  // those looks off the character. Style-LoRA groups never caption their style.
  const style = item && parameters.reference && includeCharacterStyle
    ? styleCaptionTags(parameters.style_prompt).filter(tag => !traits.has(tag))
    : []
  const unique = [...new Set([...lead, ...style, ...tags])]
  return unique.join(', ')
}

export interface DatasetExportProgress {
  processedJobs: number
  totalJobs: number
  written: number
  skipped: number
  discarded: number
}

export interface DatasetExportResult {
  blob: Blob | null
  written: number
  skipped: number
  discarded: number
}

function aborted(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

/** Read each retained image once, sequentially, through the clean export path. Never generates. */
export async function buildDatasetZip(
  api: WorkspaceApi, jobs: readonly GenerationView[], trigger: string, prefix: string, signal: AbortSignal,
  onProgress: (progress: DatasetExportProgress) => void,
  includeCharacterStyle = true,
): Promise<DatasetExportResult> {
  const zip = new ZipWriter()
  const encoder = new TextEncoder()
  let written = 0
  let skipped = 0
  let discarded = 0
  for (const [jobIndex, job] of jobs.entries()) {
    if (signal.aborted) throw new DOMException('Export cancelled.', 'AbortError')
    if (job.status !== 'succeeded' || !job.image_urls.length) skipped += Math.max(1, job.parameters.sample_count)
    else {
      const caption = encoder.encode(datasetCaption(job.parameters, trigger, prefix, includeCharacterStyle) + '\n')
      const marks = new Set(job.discarded_images ?? [])
      for (const [imageIndex, path] of job.image_urls.entries()) {
        // Review marks: discarded images never enter the dataset.
        if (marks.has(imageIndex)) { discarded += 1; continue }
        let png: Uint8Array
        try {
          const source = await api.image(path, signal)
          const url = URL.createObjectURL(source)
          try {
            png = new Uint8Array(await (await sanitizedPng(url, signal)).arrayBuffer())
          } finally {
            URL.revokeObjectURL(url)
          }
        } catch (error) {
          if (aborted(error) || (error instanceof ApiFailure && error.status === 401)) throw error
          skipped += 1
          continue
        }
        const name = String(written + 1).padStart(4, '0')
        zip.add(`${name}.png`, png)
        zip.add(`${name}.txt`, caption)
        written += 1
      }
    }
    onProgress({ processedJobs: jobIndex + 1, totalJobs: jobs.length, written, skipped, discarded })
  }
  return { blob: written ? zip.finish() : null, written, skipped, discarded }
}

/** Page through one saved experiment's groups (metadata only; images are read later). */
export async function experimentJobs(api: WorkspaceApi, experimentId: string, signal: AbortSignal): Promise<GenerationView[]> {
  const jobs: GenerationView[] = []
  let offset: number | null = 0
  while (offset !== null) {
    const page = await api.experiment(experimentId, offset, 100, signal)
    jobs.push(...page.items)
    offset = page.next_offset
  }
  return jobs
}

export async function selectedJobs(api: WorkspaceApi, ids: readonly string[], signal: AbortSignal): Promise<GenerationView[]> {
  const jobs: GenerationView[] = []
  for (const id of ids) {
    if (signal.aborted) throw new DOMException('Export cancelled.', 'AbortError')
    jobs.push(await api.generation(id, signal))
  }
  return jobs
}

export function downloadZip(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
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
