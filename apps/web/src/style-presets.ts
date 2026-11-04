/**
 * Built-in style pool presets for character-LoRA training sets. Medium and
 * technique tags only (no artist tags), preferring common Danbooru tags so the
 * model recognises them and exported captions name the style. They vary how the
 * character is drawn so the LoRA does not bind one look to the character.
 * Effects vary by model.
 *
 * Deliberately absent: chibi (changes proportions), 3D (changes the face) and
 * greyscale media — greyscale samples drop hair/eye/outfit colours, which
 * character captions do not mention, so a LoRA would learn faded colours
 * (2026-10-30).
 */
export interface StylePreset {
  id: string
  label: string
  tags: string
  /** Checked when the picker first opens. */
  defaultOn: boolean
  /** Short caution shown beside the label. */
  note?: string
}

export const STYLE_PRESETS: readonly StylePreset[] = [
  { id: 'anime', label: '动画上色', tags: 'anime coloring, lineart', defaultOn: true },
  { id: 'screencap', label: '动画截图', tags: 'anime screencap', defaultOn: true },
  { id: 'flat', label: '平涂', tags: 'flat color, simple shading, thick outlines', defaultOn: true },
  { id: 'painting', label: '厚涂', tags: 'painting (medium), realistic shading', defaultOn: true },
  { id: 'watercolor', label: '水彩', tags: 'watercolor (medium), traditional media', defaultOn: true },
  { id: 'colored-pencil', label: '彩铅', tags: 'colored pencil (medium), sketch, traditional media', defaultOn: true },
  { id: 'oil', label: '油画', tags: 'oil painting (medium), traditional media', defaultOn: true },
  { id: 'gouache', label: '水粉', tags: 'gouache (medium), traditional media', defaultOn: true },
  { id: 'marker', label: '马克笔', tags: 'marker (medium), traditional media', defaultOn: false },
  { id: 'pastel', label: '粉彩', tags: 'pastel (medium), traditional media', defaultOn: false },
  { id: 'crayon', label: '蜡笔', tags: 'crayon (medium), traditional media', defaultOn: false },
  { id: 'ink-wash', label: '墨线淡彩', tags: 'ink (medium), watercolor (medium), traditional media', defaultOn: false },
  { id: '1980s', label: '80 年代', tags: '1980s (style), retro artstyle', defaultOn: false },
  { id: '1990s', label: '90 年代', tags: '1990s (style), retro artstyle', defaultOn: true },
  { id: '2000s', label: '2000 年代', tags: '2000s (style)', defaultOn: false },
  { id: 'game-cg', label: '游戏 CG', tags: 'game cg', defaultOn: false },
  { id: 'realistic', label: '写实', tags: 'realistic, detailed shading', defaultOn: false, note: '脸型易变' },
  { id: 'pixel', label: '像素风', tags: 'pixel art', defaultOn: false, note: '细节少，易走样' },
]

export const DEFAULT_PRESET_IDS: readonly string[] = STYLE_PRESETS.filter(preset => preset.defaultOn).map(preset => preset.id)

/** Chosen presets in library order, each optionally prefixed with non-style tags (e.g. quality tags). */
export function presetStyles(prefix: string, ids: readonly string[] = DEFAULT_PRESET_IDS): string[] {
  const shared = prefix.trim()
  return STYLE_PRESETS.filter(preset => ids.includes(preset.id))
    .map(preset => shared ? `${shared}, ${preset.tags}` : preset.tags)
}
