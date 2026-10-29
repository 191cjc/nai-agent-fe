import { useEffect, useRef, useState } from 'react'
import { Plus, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { ApiFailure, errorText, type ReferenceImage, type WorkspaceApi } from './api'
import { MAX_REFERENCES, MAX_STYLE_POOL, MAX_TRAITS_LENGTH, characterRequest, type CharacterSettings } from './dataset-run'
import { VIBE_MODELS } from './store'

const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

export { characterSnapshotSummary } from './character-summary'

export interface CharacterState {
  settings: CharacterSettings
  setSettings: (update: (current: CharacterSettings) => CharacterSettings) => void
  styles: string[]
  setStyles: (update: (current: string[]) => string[]) => void
  error: (model: string) => string
}

/** Character run settings live in the dataset panel so collapsing it keeps them. */
export function useCharacterSettings(draftStyle: string): CharacterState {
  const [settings, setSettingsState] = useState<CharacterSettings>({ traits: '', mode: 'vibe', referenceIds: [], strength: '0.55', noise: '0' })
  // Until the user edits the pool it follows the live draft style, like style mode.
  const [edited, setEdited] = useState<string[] | null>(null)
  const styles = edited ?? [draftStyle]
  return {
    settings, styles,
    setSettings: update => setSettingsState(update),
    setStyles: update => setEdited(current => update(current ?? [draftStyle])),
    error: model => {
      try {
        characterRequest(settings, model, VIBE_MODELS)
        return ''
      } catch (error) {
        return error instanceof Error ? error.message : '角色设置无效。'
      }
    },
  }
}

function failureText(error: unknown): string {
  return error instanceof ApiFailure ? errorText(error) : error instanceof Error ? error.message : '操作失败，请重试。'
}

/** Owner reference images with lazily loaded thumbnails; selection is capped at four. */
function ReferencePicker({ api, selected, onChange }: {
  api: WorkspaceApi; selected: string[]; onChange: (update: (current: string[]) => string[]) => void
}) {
  const [items, setItems] = useState<ReferenceImage[]>([])
  const [urls, setUrls] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const owned = useRef<Record<string, string>>({})
  const uploaded = useRef<ReferenceImage[]>([])
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => () => { Object.values(owned.current).forEach(url => URL.revokeObjectURL(url)) }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    void (async () => {
      try {
        const { items: loaded } = await api.referenceImages(controller.signal)
        // Keep uploads that finished while this list was loading; the server list is otherwise authoritative.
        const known = new Set(loaded.map(item => item.id))
        const kept = uploaded.current.filter(item => !known.has(item.id))
        setItems([...kept, ...loaded])
        const present = new Set([...known, ...kept.map(item => item.id)])
        onChange(current => current.filter(id => present.has(id)))
        for (const [id, url] of Object.entries(owned.current)) {
          if (!present.has(id)) { URL.revokeObjectURL(url); delete owned.current[id] }
        }
      } catch (exception) {
        if (!controller.signal.aborted) setError(failureText(exception))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    })()
    return () => controller.abort()
    // Reload on explicit refresh only; local actions update the list directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, reload])

  useEffect(() => {
    const controller = new AbortController()
    for (const item of items) {
      if (owned.current[item.id]) continue
      void api.referenceImage(item.id, controller.signal).then(blob => {
        if (controller.signal.aborted || owned.current[item.id]) return
        const url = URL.createObjectURL(blob)
        owned.current[item.id] = url
        setUrls(current => ({ ...current, [item.id]: url }))
      }).catch(() => undefined)
    }
    return () => controller.abort()
  }, [api, items])

  async function upload(files: FileList | null) {
    const file = files?.[0]
    if (input.current) input.current.value = ''
    if (!file) return
    if (!['image/png', 'image/jpeg'].includes(file.type)) { setError('仅支持 PNG 或 JPEG 图片。'); return }
    if (file.size > MAX_UPLOAD_BYTES) { setError('参考图超过 8 MB。'); return }
    setBusy(true)
    setError('')
    try {
      const created = await api.uploadReferenceImage(file)
      uploaded.current = [created, ...uploaded.current]
      setItems(current => [created, ...current])
      onChange(current => current.length < MAX_REFERENCES ? [...current, created.id] : current)
    } catch (exception) {
      setError(failureText(exception))
    } finally {
      setBusy(false)
    }
  }

  async function remove(item: ReferenceImage) {
    if (!window.confirm('删除这张参考图？已完成的批跑记录不受影响。')) return
    setBusy(true)
    setError('')
    try {
      await api.deleteReferenceImage(item.id)
      setItems(current => current.filter(other => other.id !== item.id))
      uploaded.current = uploaded.current.filter(other => other.id !== item.id)
      onChange(current => current.filter(id => id !== item.id))
      const url = owned.current[item.id]
      if (url) URL.revokeObjectURL(url)
      delete owned.current[item.id]
    } catch (exception) {
      setError(failureText(exception))
    } finally {
      setBusy(false)
    }
  }

  function toggle(id: string, value: boolean) {
    if (value && selected.length >= MAX_REFERENCES) { setError(`最多选择 ${MAX_REFERENCES} 张参考图。`); return }
    setError('')
    onChange(current => value ? [...current.filter(other => other !== id), id] : current.filter(other => other !== id))
  }

  return <fieldset className="dataset-categories reference-picker" disabled={busy}>
    <legend>参考图（已选 {selected.length} / {MAX_REFERENCES}）</legend>
    <p className="prompt-hint">上传 PNG / JPEG（≤ 8 MB，边长 64–2048），或在历史图片查看器中点「设为参考图」。参考图私有保存，直到你删除。</p>
    <div className="reference-grid">
      {items.map(item => <label key={item.id} className={`reference-tile${selected.includes(item.id) ? ' selected' : ''}`}>
        {urls[item.id] ? <img src={urls[item.id]} alt={`参考图 ${item.width}×${item.height}`} /> : <span className="reference-placeholder">加载中</span>}
        <span className="reference-meta">
          <input type="checkbox" checked={selected.includes(item.id)} aria-label="选为本次参考图" onChange={event => toggle(item.id, event.target.checked)} />
          {item.width}×{item.height}{item.source === 'result' ? ' · 历史' : ''}
          <button className="icon-button" type="button" title="删除参考图" aria-label="删除参考图"
            onClick={event => { event.preventDefault(); void remove(item) }}><Trash2 size={13} /></button>
        </span>
      </label>)}
      <button className="reference-tile reference-upload" type="button" onClick={() => input.current?.click()}>
        <Upload size={18} aria-hidden="true" /><span>{busy ? '处理中...' : '上传参考图'}</span>
      </button>
      <input ref={input} type="file" accept="image/png,image/jpeg" hidden onChange={event => void upload(event.target.files)} />
    </div>
    <button className="text-action" type="button" disabled={loading} onClick={() => setReload(value => value + 1)}>刷新参考图列表</button>
    {loading && <p className="subtle" role="status">正在加载参考图...</p>}
    {error && <p className="alert" role="alert">{error}</p>}
  </fieldset>
}

/** Explicit, paid trait suggestion from the selected reference images; never auto-applied. */
function TraitAdvice({ api, referenceIds, traits, onApply }: {
  api: WorkspaceApi; referenceIds: string[]; traits: string; onApply: (traits: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  const key = referenceIds.join(',')

  useEffect(() => () => controller.current?.abort(), [])
  // A response for an earlier reference selection must not be applied to a new one.
  useEffect(() => {
    controller.current?.abort()
    controller.current = null
    setLoading(false)
    setSuggestion('')
    setError('')
  }, [key])

  async function request() {
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setLoading(true)
    setError('')
    setSuggestion('')
    try {
      const result = await api.traitAdvice(referenceIds, traits, current.signal)
      if (controller.current === current) setSuggestion(result.suggestion)
    } catch (exception) {
      if (controller.current === current && !current.signal.aborted) setError(failureText(exception))
    } finally {
      if (controller.current === current) { controller.current = null; setLoading(false) }
    }
  }

  function close() {
    controller.current?.abort()
    controller.current = null
    setOpen(false)
    setLoading(false)
    setSuggestion('')
    setError('')
  }

  if (!open) {
    return <button className="text-action" type="button" disabled={!referenceIds.length} title={referenceIds.length ? undefined : '先选择参考图'}
      onClick={() => setOpen(true)}><Sparkles size={14} aria-hidden="true" /> 根据参考图建议角色特征</button>
  }
  return <div className="dataset-export trait-advice" role="group" aria-label="角色特征 AI 建议">
    <p className="prompt-hint">将把所选 {referenceIds.length} 张参考图和当前角色特征发送给已配置的 AI 建议服务（第三方模型），每次点击是一次付费请求。建议不会自动应用。</p>
    {suggestion && <label className="field"><span>建议的角色特征（可编辑）</span>
      <textarea rows={3} value={suggestion} maxLength={MAX_TRAITS_LENGTH} spellCheck={false} onChange={event => setSuggestion(event.target.value)} /></label>}
    {error && <p className="alert" role="alert">{error}</p>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={loading || !referenceIds.length} onClick={() => void request()}>
        <Sparkles size={14} aria-hidden="true" /> {loading ? '正在分析参考图...' : suggestion ? '重新获取建议' : '获取建议'}</button>
      {suggestion && <>
        <button className="secondary" type="button" onClick={() => { onApply(suggestion.trim()); close() }}>替换</button>
        <button className="secondary" type="button" onClick={() => {
          onApply([traits.trim(), suggestion.trim()].filter(Boolean).join(', '))
          close()
        }}>追加</button>
      </>}
      <button className="text-action" type="button" onClick={close}><X size={14} aria-hidden="true" /> 关闭</button>
    </div>
  </div>
}

export function CharacterRunSettings({ api, state, model, draftStyle }: {
  api: WorkspaceApi; state: CharacterState; model: string; draftStyle: string
}) {
  const { settings, setSettings, styles, setStyles } = state
  const vibeSupported = VIBE_MODELS.includes(model.trim())

  return <>
    <ReferencePicker api={api} selected={settings.referenceIds}
      onChange={update => setSettings(current => ({ ...current, referenceIds: update(current.referenceIds) }))} />
    <label className="field"><span>角色特征（每条都会带上，导出 caption 时去掉，用触发词代替）</span>
      <textarea rows={2} value={settings.traits} maxLength={MAX_TRAITS_LENGTH} spellCheck={false}
        placeholder="例如 1girl, solo, silver hair, long hair, red eyes, black hoodie"
        onChange={event => setSettings(current => ({ ...current, traits: event.target.value }))} /></label>
    <TraitAdvice api={api} referenceIds={settings.referenceIds} traits={settings.traits}
      onApply={traits => setSettings(current => ({ ...current, traits }))} />
    <fieldset className="dataset-categories">
      <legend>生成方式</legend>
      <label className="history-select"><input type="radio" name="character-mode" checked={settings.mode === 'vibe'}
        onChange={() => setSettings(current => ({ ...current, mode: 'vibe' }))} /> Vibe Transfer（所有参考图一起使用；仅 V4 / V4.5 模型）</label>
      <label className="history-select"><input type="radio" name="character-mode" checked={settings.mode === 'img2img'}
        onChange={() => setSettings(current => ({ ...current, mode: 'img2img' }))} /> 图生图（参考图按条目轮流使用；所有模型）</label>
      {settings.mode === 'vibe' && !vibeSupported && <p className="experiment-note">当前模型不支持 Vibe Transfer，请在生成设置中选择 V4 / V4.5 模型，或改用图生图。</p>}
      {settings.mode === 'img2img' && <div className="experiment-range-fields">
        <label className="field"><span>strength（0.01–0.99，越大越偏离原图）</span>
          <input type="text" inputMode="decimal" value={settings.strength} onChange={event => setSettings(current => ({ ...current, strength: event.target.value }))} /></label>
        <label className="field"><span>noise（0–0.99）</span>
          <input type="text" inputMode="decimal" value={settings.noise} onChange={event => setSettings(current => ({ ...current, noise: event.target.value }))} /></label>
      </div>}
      {settings.mode === 'img2img' && <p className="prompt-hint">图生图的构图会受原图影响：strength 低更像角色但姿势单一，高则多样但容易走样。建议 0.5–0.7 并人工筛图。</p>}
    </fieldset>
    <fieldset className="dataset-categories">
      <legend>画风池（{styles.length} / {MAX_STYLE_POOL}，按条目轮流使用）</legend>
      <p className="prompt-hint">多种画风可减少角色 LoRA 顺带学到某一种画风。caption 不含画风。</p>
      {styles.map((style, index) => <div className="dataset-custom" key={index}>
        <input type="text" value={style} spellCheck={false} aria-label={`画风 ${index + 1}`} placeholder="画风、媒介与画质标签"
          onChange={event => setStyles(current => current.map((item, position) => position === index ? event.target.value : item))} />
        <button className="icon-button" type="button" title="移除画风" aria-label={`移除画风 ${index + 1}`} disabled={styles.length === 1}
          onClick={() => setStyles(current => current.filter((_item, position) => position !== index))}><Trash2 size={14} /></button>
      </div>)}
      <div className="dataset-custom">
        <button className="secondary" type="button" disabled={styles.length >= MAX_STYLE_POOL} onClick={() => setStyles(current => [...current, ''])}>
          <Plus size={14} aria-hidden="true" /> 添加画风</button>
        <button className="text-action" type="button" disabled={!draftStyle.trim() || styles.length >= MAX_STYLE_POOL}
          onClick={() => setStyles(current => [...current.filter(item => item.trim()), draftStyle])}>加入当前草稿画风</button>
      </div>
    </fieldset>
  </>
}
