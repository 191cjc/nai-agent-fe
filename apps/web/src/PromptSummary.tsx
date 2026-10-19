import type { GenerationRequest } from './api'
import { CHARACTER_POSITION_CENTER } from './store'
import { CHARACTER_SECTION_KEYS, SHARED_SECTION_KEYS, SECTION_LABELS, characterPrompt } from './prompt-sections'

export function PromptSummary({ parameters }: { parameters: Pick<GenerationRequest, 'style_prompt' | 'positive_prompt' | 'character_prompts' | 'auto_character_position' | 'prompt_sections' | 'prompt_comments'> }) {
  const metadata = parameters.prompt_sections
  if (metadata) return <dl className="prompt-summary section-prompt-summary">
    {parameters.prompt_comments && <div><dt>标签隐藏</dt><dd className="section-summary-state">// 开头的整行未参与生成；以下保留可恢复的原文。</dd></div>}
    {parameters.style_prompt && <div><dt>画风</dt><dd>{parameters.style_prompt}</dd></div>}
    {SHARED_SECTION_KEYS.map(key => <div key={key}><dt>公共 · {SECTION_LABELS[key]}</dt><dd>
      <span className="section-summary-state">{metadata.shared[key].enabled ? '启用' : '已隐藏 · 未参与生成'}</span>
      {metadata.shared[key].text || '（留空）'}
    </dd></div>)}
    {metadata.characters.map((person, index) => <div key={index}><dt>人物 {index + 1}</dt><dd>
      <span className="character-saved-position">{characterPrompt(person.sections, parameters.prompt_comments === true).trim()
        ? parameters.auto_character_position ? '自动位置' : `手动位置 X ${person.x.toFixed(2)} · Y ${person.y.toFixed(2)}`
        : `未参与生成 · ${parameters.auto_character_position ? '自动模式 · ' : ''}保留手动位置 X ${person.x.toFixed(2)} · Y ${person.y.toFixed(2)}`}</span>
      {CHARACTER_SECTION_KEYS.map(key => <span className="section-summary-line" key={key}>
        <strong>{SECTION_LABELS[key]}</strong><span className="section-summary-state">{person.sections[key].enabled ? '启用' : '已隐藏 · 未参与生成'}</span>
        <span>{person.sections[key].text || '（留空）'}</span>
      </span>)}
    </dd></div>)}
  </dl>
  return <dl className="prompt-summary">
    {parameters.prompt_comments && <div><dt>标签隐藏</dt><dd className="section-summary-state">// 开头的整行未参与生成；以下保留可恢复的原文。</dd></div>}
    {parameters.style_prompt && <div><dt>画风</dt><dd>{parameters.style_prompt}</dd></div>}
    {parameters.positive_prompt && <div><dt>公共</dt><dd>{parameters.positive_prompt}</dd></div>}
    {(parameters.character_prompts ?? []).map((character, index) =>
      <div key={index}><dt>人物 {index + 1}</dt><dd>{character.prompt}
        <span className="character-saved-position">{parameters.auto_character_position
          ? '自动位置'
          : `手动位置 X ${(character.x ?? CHARACTER_POSITION_CENTER).toFixed(2)} · Y ${(character.y ?? CHARACTER_POSITION_CENTER).toFixed(2)}`}</span>
      </dd></div>)}
  </dl>
}
