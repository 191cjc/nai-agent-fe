import { useLayoutEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Eye, EyeOff, Pencil } from 'lucide-react'
import { adjustPromptTagWeight, formatPromptTags, parsePromptTags, togglePromptTagHidden, type PromptTag } from './prompt-weights'

interface PromptEditorProps {
  id: string
  label: string
  value: string
  placeholder: string
  rows?: number
  maxLength?: number
  onChange: (value: string) => void
  onFocus?: () => void
}

export function PromptEditor({ id, label, value, placeholder, rows = 2, maxLength = 3000, onChange, onFocus }: PromptEditorProps) {
  const [editing, setEditing] = useState(() => value.length === 0)
  const [fieldHeight, setFieldHeight] = useState<number | null>(null)
  const [weightError, setWeightError] = useState<{ value: string; text: string } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const focusOnEdit = useRef(false)
  const tags = parsePromptTags(value, true)
  const error = weightError?.value === value ? weightError.text : ''
  const hasOriginalSyntax = tags.some(tag => tag.weight === null)
  const manualOnly = tags.some(tag => tag.manualOnly)

  useLayoutEffect(() => {
    if (editing && focusOnEdit.current) {
      focusOnEdit.current = false
      textareaRef.current?.focus()
    }
  }, [editing])

  function adjust(tag: PromptTag, direction: -1 | 1) {
    const next = adjustPromptTagWeight(value, tag, direction)
    if (next === null) return
    if (next.length > maxLength) {
      setWeightError({ value, text: `调整后将超过 ${maxLength} 字符，请先手动精简提示词。` })
      return
    }
    setWeightError(null)
    onChange(next)
  }

  function toggleHidden(tag: PromptTag) {
    const next = togglePromptTagHidden(value, tag)
    if (next === null) return
    if (next.length > maxLength) {
      setWeightError({ value, text: `隐藏或恢复后将超过 ${maxLength} 字符，请先手动精简提示词。` })
      return
    }
    setWeightError(null)
    onChange(next)
  }

  return <div className="prompt-editor" role="group" aria-label={label} onFocus={onFocus}>
    {editing ? <textarea ref={textareaRef} id={id} aria-label={label} value={value} maxLength={maxLength} rows={rows}
      style={fieldHeight === null ? undefined : { height: fieldHeight }}
      placeholder={placeholder} onBlur={event => {
        // Keep the pending pointer click at the same position when tags replace
        // a short textarea, including after the textarea was manually resized.
        setFieldHeight(event.currentTarget.getBoundingClientRect().height)
        const next = formatPromptTags(value)
        if (next.length > maxLength) {
          setWeightError({ value, text: `每行一个标签将超过 ${maxLength} 字符，已保留原文，请手动精简后再编辑。` })
        } else if (next !== value) {
          setWeightError(null)
          onChange(next)
        }
        setEditing(false)
      }}
      onChange={event => { setWeightError(null); onChange(event.target.value) }} />
      : <div className="prompt-tag-view" style={{ height: fieldHeight ?? Math.max(68, rows * 20 + 18) }}>
        {tags.length ? <ul className="prompt-tag-list" aria-label={`${label}标签`}>
          {tags.map((tag, index) => <li className={`prompt-tag${tag.weight === null ? ' original' : ''}${tag.hidden ? ' muted' : ''}`} key={index}>
            <span className="prompt-tag-text">{tag.text}</span>
            {tag.hidden && <span className="prompt-tag-hidden-label">已隐藏</span>}
            <span className="prompt-tag-weight" aria-live="polite" aria-atomic="true"
              title={tag.weight === null ? '保留原文，请手动编辑此表达式' : `权重 ${tag.weight}`}>
              {tag.weight ?? '原文'}
            </span>
            <span className="prompt-weight-controls">
              <button className="prompt-weight-button" type="button" disabled={tag.hidden || tag.weight === null}
                aria-label={`${label}：${tag.text}，增加权重 0.1`} title="增加权重 0.1" onClick={() => adjust(tag, 1)}>
                <ChevronUp size={12} aria-hidden="true" />
              </button>
              <button className="prompt-weight-button" type="button" disabled={tag.hidden || tag.weight === null}
                aria-label={`${label}：${tag.text}，减少权重 0.1`} title="减少权重 0.1" onClick={() => adjust(tag, -1)}>
                <ChevronDown size={12} aria-hidden="true" />
              </button>
            </span>
            <button className="prompt-tag-visibility" type="button" disabled={manualOnly}
              aria-label={`${label}：${tag.hidden ? '恢复' : '隐藏'}${tag.text}`} aria-pressed={Boolean(tag.hidden)}
              title={manualOnly ? '复杂多行或行首标记请手动编辑，保留原文' : tag.hidden ? '恢复此标签' : '暂时隐藏此标签'}
              onClick={() => toggleHidden(tag)}>
              {tag.hidden ? <Eye size={13} aria-hidden="true" /> : <EyeOff size={13} aria-hidden="true" />}
            </button>
          </li>)}
        </ul> : <p className="prompt-tag-placeholder">{placeholder}</p>}
      </div>}
    <div className="prompt-editor-footer">
      {error ? <p className="prompt-weight-error" role="alert">{error}</p>
        : <span className="prompt-edit-hint" title={manualOnly ? '复杂多行表达式或行首 // 原文保持不变，请手动编辑隐藏标记。' : undefined}>
          {editing ? '失焦后每行一个标签；// 隐藏整行' : manualOnly ? '复杂多行或行首标记保留原文，请手动编辑。' : hasOriginalSyntax ? '复杂语法保留原文，可手动编辑。' : '权重每次调整 0.1；隐藏的标签不参与生成'}</span>}
      <button className="prompt-manual-edit" type="button" aria-label={`手动编辑${label}`} disabled={editing}
        style={{ visibility: editing ? 'hidden' : undefined }}
        onClick={() => { setWeightError(null); focusOnEdit.current = true; setEditing(true) }}>
        <Pencil size={12} aria-hidden="true" /> 手动编辑
      </button>
    </div>
  </div>
}
