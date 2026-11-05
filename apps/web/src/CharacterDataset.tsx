import { useEffect, useRef, useState } from 'react'
import { Palette, Plus, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { ReferenceThumb } from './ReferencePreview'
import { ApiFailure, errorText, type Capabilities, type ReferenceImage, type WorkspaceApi } from './api'
import { GPT_SIZES, MAX_REFERENCES, MAX_STYLE_POOL, MAX_TRAITS_LENGTH, characterRequest, type CharacterSettings, type GptSize } from './dataset-run'
import { PRECISE_MODELS, VIBE_MODELS } from './store'
import type { PreciseType } from './api'
import { DEFAULT_PRESET_IDS, STYLE_PRESETS, presetStyles } from './style-presets'

const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

export { characterSnapshotSummary } from './character-summary'

export interface CharacterState {
  /** null until checked: whether the server has a GPT image key configured. */
  gpt: Capabilities | null
  setGpt: (gpt: Capabilities) => void
  settings: CharacterSettings
  setSettings: (update: (current: CharacterSettings) => CharacterSettings) => void
  styles: string[]
  setStyles: (update: (current: string[]) => string[]) => void
  error: (model: string) => string
}

/** Character run settings live in the dataset panel so collapsing it keeps them. */
export function useCharacterSettings(draftStyle: string): CharacterState {
  const [settings, setSettingsState] = useState<CharacterSettings>({ traits: '', mode: 'vibe', referenceIds: [], strength: '0.55', noise: '0', information: '1', vibeStrength: '1',
    gptSize: 'portrait', gptQuality: 'auto', gptSamples: '1', gptConcurrency: '', preciseType: 'character', preciseStrength: '1', preciseFidelity: '1' })
  // Until the user edits the pool it follows the live draft style, like style mode.
  const [edited, setEdited] = useState<string[] | null>(null)
  const styles = edited ?? [draftStyle]
  const [gpt, setGpt] = useState<Capabilities | null>(null)
  return {
    gpt, setGpt, settings, styles,
    setSettings: update => setSettingsState(update),
    setStyles: update => setEdited(current => update(current ?? [draftStyle])),
    error: model => {
      if (settings.mode === 'gpt' && !gpt?.gpt_image) return 'GPT 生图未配置，请在服务器上设置 NAI_GPT_IMAGE_API_KEY。'
      try {
        characterRequest(settings, model, VIBE_MODELS, PRECISE_MODELS)
        return ''
      } catch (error) {
        return error instanceof Error ? error.message : '角色设置无效。'
      }
    },
  }
}

/** Mirrors the server template so the user sees exactly what GPT receives. */
function gptPromptPreview(traits: string, style: string): string {
  return [
    'Use the attached reference image(s); they all show the same character.',
    'Draw exactly this character: keep the face, hair, eyes, outfit, accessories and weapon identical to the references.',
    `Character: ${traits.trim()}`,
    'Scene and pose: <第 1 条内容提示词>',
    ...(style.trim() ? [`Art style: ${style.trim()}`] : []),
    'One character only. No text, no watermark, no signature.',
  ].join('\n')
}

function failureText(error: unknown): string {
  return error instanceof ApiFailure ? errorText(error) : error instanceof Error ? error.message : '操作失败，请重试。'
}

/** Owner reference images with lazily loaded thumbnails; selection is capped at four. */
function ReferencePicker({ api, selected, onChange }: {
  api: WorkspaceApi; selected: string[]; onChange: (update: (current: string[]) => string[]) => void
}) {
  const [items, setItems] = useState<ReferenceImage[]>([])
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const uploaded = useRef<ReferenceImage[]>([])
  const input = useRef<HTMLInputElement>(null)

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
      {items.map(item => <div key={item.id} className={`reference-tile${selected.includes(item.id) ? ' selected' : ''}`}>
        <ReferenceThumb api={api} id={item.id} label={`参考图 ${item.width}×${item.height}`} />
        <span className="reference-meta">
          <label className="reference-select">
            <input type="checkbox" checked={selected.includes(item.id)} aria-label="选为本次参考图" onChange={event => toggle(item.id, event.target.checked)} />
            {item.width}×{item.height}{item.source === 'result' ? ' · 历史' : ''}
          </label>
          <button className="icon-button" type="button" title="删除参考图" aria-label="删除参考图"
            onClick={event => { event.preventDefault(); void remove(item) }}><Trash2 size={13} /></button>
        </span>
      </div>)}
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
  const { settings, setSettings, styles, setStyles, gpt, setGpt } = state

  useEffect(() => {
    const controller = new AbortController()
    api.capabilities(controller.signal).then(setGpt).catch(() => {
      if (!controller.signal.aborted) setGpt({ gpt_image: false, gpt_image_model: null })
    })
    return () => controller.abort()
    // setGpt is a stable state setter wrapper recreated per render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api])
  // Optional shared prefix (e.g. quality tags), empty by default. Never the draft style:
  // that is itself a style and would mix into every preset.
  const [prefix, setPrefix] = useState('')
  const [presetIds, setPresetIds] = useState<readonly string[]>(DEFAULT_PRESET_IDS)
  const chosenPresets = presetStyles(prefix, presetIds)
  const vibeSupported = VIBE_MODELS.includes(model.trim())
  const preciseSupported = PRECISE_MODELS.includes(model.trim())

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
      <label className="history-select"><input type="radio" name="character-mode" checked={settings.mode === 'precise'}
        onChange={() => setSettings(current => ({ ...current, mode: 'precise' }))} /> 精准参考 Precise Reference（参考图按条目轮流使用；仅 V4.5 模型）</label>
      <label className="history-select"><input type="radio" name="character-mode" checked={settings.mode === 'gpt'} disabled={!gpt?.gpt_image}
        onChange={() => setSettings(current => ({ ...current, mode: 'gpt' }))} /> GPT 参考图生成（{gpt?.gpt_image_model ?? 'GPT 生图'}；与 NovelAI 无关{gpt && !gpt.gpt_image ? '；未配置' : ''}）</label>
      {settings.mode === 'gpt' && <>
        <p className="prompt-hint">GPT 模式不使用 NovelAI 的模型、采样器、步数、CFG 和负面提示词。所有参考图会和下方提示词一起发送给中转站的 GPT 生图模型；每条一次付费调用，约 1–2 分钟；暴露或有版权的内容可能被审核拒绝（记为失败，继续下一条）。</p>
        <div className="experiment-range-fields">
          <label className="field"><span>输出尺寸</span>
            <select value={settings.gptSize} onChange={event => setSettings(current => ({ ...current, gptSize: event.target.value as GptSize }))}>
              {(Object.keys(GPT_SIZES) as GptSize[]).map(size => <option key={size} value={size}>{GPT_SIZES[size].label}</option>)}
            </select></label>
          <label className="field"><span>质量</span>
            <select value={settings.gptQuality} onChange={event => setSettings(current => ({ ...current, gptQuality: event.target.value as CharacterSettings['gptQuality'] }))}>
              <option value="auto">自动</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option>
            </select></label>
          <label className="field"><span>每条张数（1–4）</span>
            <input type="text" inputMode="numeric" value={settings.gptSamples} onChange={event => setSettings(current => ({ ...current, gptSamples: event.target.value }))} /></label>
          <label className="field"><span>同时生成条数（1–{gpt?.gpt_concurrency_max ?? 16}；留空为最大，运行中可在队列里调整）</span>
            <input type="text" inputMode="numeric" placeholder={String(gpt?.gpt_concurrency_max ?? '')} value={settings.gptConcurrency}
              onChange={event => setSettings(current => ({ ...current, gptConcurrency: event.target.value }))} /></label>
        </div>
        <details className="dataset-category"><summary><strong>第 1 条的提示词预览</strong></summary>
          <pre className="request-snapshot-json">{gptPromptPreview(settings.traits, styles[0] ?? '')}</pre></details>
      </>}
      {settings.mode === 'vibe' && <div className="experiment-range-fields">
        <label className="field"><span>信息提取度（0.01–1，越高越贴近参考图中的角色，越低越只取风格）</span>
          <input type="text" inputMode="decimal" value={settings.information} onChange={event => setSettings(current => ({ ...current, information: event.target.value }))} /></label>
        <label className="field"><span>Vibe 强度（0.01–1，生成时参考图的影响力，越高越像参考图）</span>
          <input type="text" inputMode="decimal" value={settings.vibeStrength} onChange={event => setSettings(current => ({ ...current, vibeStrength: event.target.value }))} /></label>
      </div>}
      {settings.mode === 'vibe' && <p className="prompt-hint">每张参考图会先编码成 vibe（NovelAI 对编码另行扣费），结果按参考图、模型和信息提取度缓存在服务器上，之后的条目和批跑会复用，不再重复扣费。</p>}
      {settings.mode === 'vibe' && !vibeSupported && <p className="experiment-note">当前模型不支持 Vibe Transfer，请在生成设置中选择 V4 / V4.5 模型，或改用图生图。</p>}
      {settings.mode === 'img2img' && <div className="experiment-range-fields">
        <label className="field"><span>strength（0.01–0.99，越大越偏离原图）</span>
          <input type="text" inputMode="decimal" value={settings.strength} onChange={event => setSettings(current => ({ ...current, strength: event.target.value }))} /></label>
        <label className="field"><span>noise（0–0.99）</span>
          <input type="text" inputMode="decimal" value={settings.noise} onChange={event => setSettings(current => ({ ...current, noise: event.target.value }))} /></label>
      </div>}
      {settings.mode === 'precise' && <div className="experiment-range-fields">
        <label className="field"><span>参考内容</span>
          <select value={settings.preciseType} onChange={event => setSettings(current => ({ ...current, preciseType: event.target.value as PreciseType }))}>
            <option value="character">角色（只取角色外观，画风由画风池决定）</option>
            <option value="character&style">角色 + 画风</option>
            <option value="style">只取画风</option>
          </select></label>
        <label className="field"><span>强度（0.01–1，参考图的影响力）</span>
          <input type="text" inputMode="decimal" value={settings.preciseStrength} onChange={event => setSettings(current => ({ ...current, preciseStrength: event.target.value }))} /></label>
        <label className="field"><span>保真度（0–1，越高越贴近参考图细节）</span>
          <input type="text" inputMode="decimal" value={settings.preciseFidelity} onChange={event => setSettings(current => ({ ...current, preciseFidelity: event.target.value }))} /></label>
      </div>}
      {settings.mode === 'precise' && <p className="prompt-hint">精准参考不改变构图，姿势和场景来自提示词，适合角色训练集；每条只用一张参考图（多张时按条目轮流）。NovelAI 对精准参考会额外扣 Anlas。训练角色 LoRA 建议选「角色」，让画风池负责画风。</p>}
      {settings.mode === 'precise' && !preciseSupported && <p className="experiment-note">当前模型不支持精准参考，请在生成设置中选择 V4.5 模型。</p>}
      {settings.mode === 'img2img' && <p className="prompt-hint">图生图的构图会受原图影响：strength 低更像角色但姿势单一，高则多样但容易走样。建议 0.5–0.7 并人工筛图。</p>}
    </fieldset>
    <fieldset className="dataset-categories">
      <legend>画风池（{styles.length} / {MAX_STYLE_POOL}，按条目轮流使用）</legend>
      <p className="prompt-hint">多种画风可减少角色 LoRA 顺带学到某一种画风。导出时默认把每张图的画风写进 caption，让画风与角色分开学习。建议 8–12 种：再多每种画风只剩一两张，作用不大。</p>
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
      <div className="dataset-style-presets">
        <span>预设画风（已选 {presetIds.length} 个）</span>
        <div className="style-preset-picks" role="group" aria-label="选择预设画风">
          {STYLE_PRESETS.map(preset => <label key={preset.id} title={preset.tags}>
            <input type="checkbox" checked={presetIds.includes(preset.id)}
              onChange={event => setPresetIds(current => event.target.checked ? [...current, preset.id] : current.filter(id => id !== preset.id))} />
            {preset.label}{preset.note && <small>（{preset.note}）</small>}
          </label>)}
        </div>
        <div className="dataset-custom">
          <button className="text-action" type="button" onClick={() => setPresetIds(DEFAULT_PRESET_IDS)}>恢复推荐</button>
          <button className="text-action" type="button" onClick={() => setPresetIds(STYLE_PRESETS.map(preset => preset.id))}>全选</button>
          <button className="text-action" type="button" onClick={() => setPresetIds([])}>全不选</button>
        </div>
        <input type="text" value={prefix} spellCheck={false} aria-label="预设公共前缀"
          placeholder="可选：公共前缀，只填质量词等非画风标签，例如 best quality, very aesthetic"
          onChange={event => setPrefix(event.target.value)} />
        <div className="dataset-custom">
          <button className="secondary" type="button" disabled={!chosenPresets.length} onClick={() => {
            if (styles.some(item => item.trim()) && !window.confirm('用所选预设画风覆盖当前画风池？')) return
            setStyles(() => chosenPresets.slice(0, MAX_STYLE_POOL))
          }}><Palette size={14} aria-hidden="true" /> 填入所选（覆盖）</button>
          <button className="text-action" type="button" disabled={!chosenPresets.length || styles.filter(item => item.trim()).length >= MAX_STYLE_POOL}
            onClick={() => setStyles(current => {
              const kept = current.filter(item => item.trim())
              const added = chosenPresets.filter(item => !kept.includes(item))
              return [...kept, ...added].slice(0, MAX_STYLE_POOL)
            })}>追加所选（最多 {MAX_STYLE_POOL} 个）</button>
        </div>
        {chosenPresets.length > MAX_STYLE_POOL && <p className="experiment-note">已选 {chosenPresets.length} 个，超过画风池上限 {MAX_STYLE_POOL}，只会填入前 {MAX_STYLE_POOL} 个。</p>}
        <p className="prompt-hint">预设只用常见的媒介和技法标签，不含画师标签；鼠标悬停可看具体标签，填入后可自由修改。不同模型效果不同，建议先用 3–5 条试跑。</p>
      </div>
    </fieldset>
  </>
}
