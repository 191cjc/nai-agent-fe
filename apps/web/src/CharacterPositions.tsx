import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { observer } from 'mobx-react-lite'
import { RotateCcw } from 'lucide-react'
import {
  CHARACTER_POSITION_CENTER, CHARACTER_POSITION_MAX, CHARACTER_POSITION_MIN,
  type GenerationStore,
} from './store'

interface MarkerDrag {
  pointerId: number
  characterId: string
  target: HTMLButtonElement
  offsetX: number
  offsetY: number
}

function boundedCoordinate(value: number): number {
  return Math.round(Math.max(CHARACTER_POSITION_MIN, Math.min(CHARACTER_POSITION_MAX, value)) * 100) / 100
}

export const CharacterPositions = observer(({ generation }: { generation: GenerationStore }) => {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const boardRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<MarkerDrag | null>(null)
  const characters = generation.draft.character_prompts
  const automatic = generation.draft.auto_character_position
  const characterIds = characters.map(character => character.id).join(',')
  const selected = characters.find(character => character.id === selectedId) ?? characters[0]
  const selectedIndex = characters.findIndex(character => character.id === selected?.id)
  const width = Number(generation.draft.width)
  const height = Number(generation.draft.height)
  const validCanvas = [width, height].every(value => Number.isInteger(value) && value >= 64 && value <= 2048 && value % 64 === 0)
  const aspectRatio = validCanvas ? width / height : 1

  const endDrag = useCallback(() => {
    const drag = dragRef.current
    dragRef.current = null
    if (drag?.target.hasPointerCapture(drag.pointerId)) drag.target.releasePointerCapture(drag.pointerId)
  }, [])

  useEffect(() => {
    const drag = dragRef.current
    if (automatic || (drag && !characterIds.split(',').includes(drag.characterId))) endDrag()
  }, [automatic, characterIds, endDrag])

  useEffect(() => endDrag, [endDrag])

  function startDrag(event: PointerEvent<HTMLButtonElement>, id: string) {
    if (generation.draft.auto_character_position || event.button !== 0 || !event.isPrimary || dragRef.current) return
    const character = generation.draft.character_prompts.find(character => character.id === id)
    const board = boardRef.current?.getBoundingClientRect()
    if (!character || !board?.width || !board.height) return
    event.preventDefault()
    setSelectedId(id)
    event.currentTarget.focus({ preventScroll: true })
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = {
      pointerId: event.pointerId, characterId: id, target: event.currentTarget,
      offsetX: event.clientX - board.left - character.x * board.width,
      offsetY: event.clientY - board.top - character.y * board.height,
    }
  }

  function moveDrag(event: PointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    if (generation.draft.auto_character_position || !generation.draft.character_prompts.some(character => character.id === drag.characterId)) {
      endDrag()
      return
    }
    const board = boardRef.current?.getBoundingClientRect()
    if (!board?.width || !board.height) return
    event.preventDefault()
    generation.setCharacterPosition(drag.characterId,
      boundedCoordinate((event.clientX - board.left - drag.offsetX) / board.width),
      boundedCoordinate((event.clientY - board.top - drag.offsetY) / board.height))
  }

  function finishDrag(event: PointerEvent<HTMLButtonElement>) {
    if (dragRef.current?.pointerId === event.pointerId) endDrag()
  }

  function adjustPosition(event: KeyboardEvent<HTMLButtonElement>, id: string) {
    if (generation.draft.auto_character_position || event.altKey || event.ctrlKey || event.metaKey) return
    const dx = event.key === 'ArrowLeft' ? -0.01 : event.key === 'ArrowRight' ? 0.01 : 0
    const dy = event.key === 'ArrowUp' ? -0.01 : event.key === 'ArrowDown' ? 0.01 : 0
    if (!dx && !dy) return
    const character = generation.draft.character_prompts.find(character => character.id === id)
    if (!character) return
    event.preventDefault()
    setSelectedId(id)
    generation.setCharacterPosition(id, boundedCoordinate(character.x + dx), boundedCoordinate(character.y + dy))
  }

  if (!selected) return null

  return <section className="character-positions" aria-labelledby="character-positions-title">
    <div className="character-position-heading"><h4 id="character-positions-title">人物位置</h4>
      <label className="character-position-mode">定位方式
        <select value={automatic ? 'auto' : 'manual'} onChange={event => {
          endDrag()
          generation.setField('auto_character_position', event.target.value === 'auto')
        }}>
          <option value="manual">手动</option>
          <option value="auto">自动</option>
        </select>
      </label></div>
    {automatic ? <p className="prompt-hint">由 NovelAI 自动安排人物位置。已保留手动坐标，切回手动可继续调整。</p>
      : <div className="character-position-body">
      <div className="character-position-stage">
        <div className="character-position-board" ref={boardRef}
          style={{ aspectRatio, width: `min(100%, ${Math.min(300, 230 * aspectRatio)}px)` }}
          role="group" aria-label="画布人物位置预览" aria-describedby="character-position-help">
          {characters.map((character, index) => <button key={character.id} type="button"
            className={`character-position-marker${selected.id === character.id ? ' selected' : ''}${character.prompt.trim() ? '' : ' empty'}`}
            style={{ left: `${character.x * 100}%`, top: `${character.y * 100}%` }}
            aria-pressed={selected.id === character.id} aria-describedby="character-position-help"
            aria-label={`人物 ${index + 1}，X ${character.x.toFixed(2)}，Y ${character.y.toFixed(2)}${character.prompt.trim() ? '' : '，留空未提交'}`}
            onFocus={() => setSelectedId(character.id)} onClick={() => setSelectedId(character.id)} onKeyDown={event => adjustPosition(event, character.id)}
            onPointerDown={event => startDrag(event, character.id)} onPointerMove={moveDrag}
            onPointerUp={finishDrag} onPointerCancel={finishDrag} onLostPointerCapture={finishDrag}>
            {index + 1}
          </button>)}
        </div>
      </div>
      <div className="character-position-controls">
        <div className="character-position-selection" role="group" aria-label="选择要定位的人物">
          {characters.map((character, index) => <button type="button" key={character.id}
            className={selected.id === character.id ? 'selected' : ''} aria-pressed={selected.id === character.id}
            onClick={() => setSelectedId(character.id)}>人物 {index + 1}{!character.prompt.trim() && <span>留空</span>}</button>)}
        </div>
        <p className="character-position-readout">人物 {selectedIndex + 1}<span>X {selected.x.toFixed(2)} · Y {selected.y.toFixed(2)}</span></p>
        <button className="text-action" type="button" onClick={() => generation.setCharacterPosition(selected.id, CHARACTER_POSITION_CENTER, CHARACTER_POSITION_CENTER)}>
          <RotateCcw size={13} aria-hidden="true" /> 当前人物居中
        </button>
        <p className="prompt-hint" id="character-position-help">拖动编号定位，重叠时先选择人物。聚焦编号后可用方向键微调，每次 0.01。坐标范围 0.1–0.9，仅引导人物位置。</p>
      </div>
    </div>}
  </section>
})
