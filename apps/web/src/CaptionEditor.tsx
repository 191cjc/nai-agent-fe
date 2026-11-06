import { observer } from 'mobx-react-lite'
import { useState } from 'react'
import { PencilLine, RotateCcw } from 'lucide-react'
import { errorText, type GenerationView } from './api'
import { contentCaption } from './dataset-export'
import { translatePrompt } from './prompt-zh'
import type { SavedResultsStore } from './saved-results'

const MAX_CAPTION = 3000

/**
 * The group's training caption (content tags) with an edit that only changes the exported
 * caption: no generation, the frozen parameters stay. Lazy-loaded with the export helpers.
 */
export const CaptionEditor = observer(({ job, saved }: { job: GenerationView; saved: SavedResultsStore }) => {
  const [draft, setDraft] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const override = job.caption_override ?? null
  const current = contentCaption(job.parameters, override)

  async function save(caption: string | null) {
    setBusy(true)
    setError('')
    try {
      await saved.setCaption(caption)
      setDraft(null)
    } catch (failure) {
      setError(errorText(failure))
    } finally {
      setBusy(false)
    }
  }

  return <div className="caption-editor">
    {draft === null ? <>
      <p className="dataset-item-prompt" aria-label="导出训练词">
        训练词（导出 caption）{override ? <span className="caption-edited">已修改</span> : null}：{current}
      </p>
      {override && <p className="dataset-item-prompt-zh">中文：{translatePrompt(override)}</p>}
      <div className="caption-editor-actions">
        <button className="text-action" type="button" disabled={busy} title="只改导出时的训练词，不会重新生成"
          onClick={() => { setError(''); setDraft(current) }}><PencilLine size={14} aria-hidden="true" /> 修改训练词</button>
        {override && <button className="text-action" type="button" disabled={busy}
          onClick={() => { if (window.confirm('恢复为提示词自动生成的训练词？')) void save(null) }}>
          <RotateCcw size={14} aria-hidden="true" /> 恢复默认</button>}
      </div>
    </> : <div className="rerun-batch" role="group" aria-label="修改训练词">
      <p><strong>修改训练词</strong>：只影响导出的 caption，不重新生成、不付费。触发词、导出前缀和角色训练集的画风在导出时自动加在前面，这里只写内容标签。</p>
      <label className="field"><span>训练词</span>
        <textarea rows={3} value={draft} maxLength={MAX_CAPTION} spellCheck={false} disabled={busy}
          onChange={event => setDraft(event.target.value)} /></label>
      <span className="dataset-item-zh">{translatePrompt(draft)}</span>
      <div className="rerun-batch-actions">
        <button type="button" disabled={busy || !draft.trim()} onClick={() => void save(draft.trim())}>{busy ? '正在保存...' : '保存'}</button>
        <button className="secondary" type="button" disabled={busy} onClick={() => setDraft(null)}>取消</button>
      </div>
    </div>}
    {error && <p className="alert" role="alert">训练词未保存：{error}</p>}
  </div>
})
