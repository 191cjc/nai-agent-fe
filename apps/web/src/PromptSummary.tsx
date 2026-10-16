import type { GenerationRequest } from './api'
import { CHARACTER_POSITION_CENTER } from './store'

export function PromptSummary({ parameters }: { parameters: Pick<GenerationRequest, 'style_prompt' | 'positive_prompt' | 'character_prompts' | 'auto_character_position'> }) {
  return <dl className="prompt-summary">
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
