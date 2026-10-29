/**
 * Built-in style pool presets for character-LoRA training sets. Medium and
 * technique tags only (no artist tags): they vary how the character is drawn
 * so the LoRA does not bind one look to the character. Effects vary by model.
 */
export interface StylePreset {
  label: string
  tags: string
}

export const STYLE_PRESETS: readonly StylePreset[] = [
  { label: '动画上色', tags: 'anime coloring, cel shading, clean lineart' },
  { label: '平涂', tags: 'flat color, simple shading, thick outlines' },
  { label: '厚涂', tags: 'impasto, painterly, thick brushstrokes' },
  { label: '水彩', tags: 'watercolor (medium), traditional media, soft colors' },
  { label: '铅笔素描', tags: 'sketch, pencil (medium), monochrome, greyscale' },
  { label: '半写实', tags: 'semi-realistic, detailed shading, soft lighting' },
  { label: '复古 90 年代', tags: '1990s (style), retro artstyle' },
  { label: '像素风', tags: 'pixel art' },
]

/** Optionally prefix each preset with user-entered non-style tags (e.g. quality tags). */
export function presetStyles(prefix: string): string[] {
  const shared = prefix.trim()
  return STYLE_PRESETS.map(preset => shared ? `${shared}, ${preset.tags}` : preset.tags)
}
