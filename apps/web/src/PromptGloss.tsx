import type { DatasetItem } from './api'
import { translatePrompt } from './prompt-zh'

/** Chinese gloss of one item's training prompt (scene and each person). Display only. */
export function datasetItemZh(item: DatasetItem): string {
  return [translatePrompt(item.prompt), ...(item.characters ?? []).map((character, index) => `人物 ${index + 1}：${translatePrompt(character.prompt)}`)].join(' ｜ ')
}

/** Lazy-loaded with the tag gloss table so the main bundle stays small. */
export function DatasetItemGloss({ item, style }: { item: DatasetItem; style?: string }) {
  const styleZh = style ? translatePrompt(style) : ''
  // Only show the style line when at least one tag has a gloss.
  const styleKnown = Boolean(style && styleZh !== style.split(',').map(tag => tag.trim()).filter(Boolean).join('，'))
  return <>
    <p className="dataset-item-prompt-zh" aria-label="训练词中文说明">中文：{datasetItemZh(item)}</p>
    {styleKnown && <p className="dataset-item-prompt-zh" aria-label="画风中文说明">画风中文：{styleZh}</p>}
  </>
}
