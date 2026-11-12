/** Independent character style pools: medium and technique only, no identity or framing. */
import type { CharacterMode } from './character-prompts'

export interface StylePreset {
  id: string
  label: string
  tags: string
  defaultOn: boolean
  note?: string
}

const GPT_PRESETS: readonly StylePreset[] = [
  { id: 'gpt-design', label: '日系角色设定稿', tags: 'anime coloring, clean lineart, flat color, simple shading', defaultOn: true },
  { id: 'gpt-commercial', label: '清爽商业插画', tags: 'digital illustration, soft shading, clean edges, full color', defaultOn: true },
  { id: 'gpt-painting', label: '清晰轻厚涂', tags: 'digital painting, crisp edges, defined color blocks, restrained brushwork', defaultOn: true },
  { id: 'gpt-colored-lines', label: '彩色线描插画', tags: 'colored lineart, fine lines, light color washes, full color', defaultOn: true },
  { id: 'gpt-watercolor', label: '水彩', tags: 'watercolor (medium), traditional media', defaultOn: false, note: '人工筛选细节' },
  { id: 'gpt-pencil', label: '彩铅', tags: 'colored pencil (medium), traditional media', defaultOn: false, note: '人工筛选细节' },
]

const PRECISE_PRESETS: readonly StylePreset[] = [
  { id: 'precise-screencap', label: '动画截图／赛璐璐', tags: 'anime screencap, cel shading, lineart', defaultOn: true },
  { id: 'precise-1990s', label: '90 年代彩色动画', tags: '1990s (style), retro artstyle, anime coloring, full color', defaultOn: true },
  { id: 'precise-game-cg', label: '二次元游戏 CG', tags: 'game cg, detailed lineart, anime coloring', defaultOn: true },
  { id: 'precise-fantasy-painting', label: '清晰幻想厚涂', tags: 'fantasy illustration, digital painting, hard edges, detailed shading', defaultOn: true },
  { id: 'precise-watercolor', label: '水彩', tags: 'watercolor (medium), traditional media', defaultOn: false, note: '人工筛选细节' },
  { id: 'precise-gouache', label: '水粉', tags: 'gouache (medium), traditional media', defaultOn: false, note: '人工筛选细节' },
]

export function characterStylePresets(mode: CharacterMode): readonly StylePreset[] {
  return mode === 'gpt' ? GPT_PRESETS : PRECISE_PRESETS
}

export function defaultCharacterStyles(mode: CharacterMode): string[] {
  return characterStylePresets(mode).filter(preset => preset.defaultOn).map(preset => preset.tags)
}

/** Chosen presets in library order, optionally prefixed with non-style quality tags. */
export function presetStyles(prefix: string, ids: readonly string[], mode: CharacterMode): string[] {
  const shared = prefix.trim()
  return characterStylePresets(mode).filter(preset => ids.includes(preset.id))
    .map(preset => shared ? `${shared}, ${preset.tags}` : preset.tags)
}
