import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { observer } from 'mobx-react-lite'
import {
  ArrowDownToLine, ArrowLeft, ArrowRight, Check,
  FlaskConical, History, Image as ImageIcon, LogOut, Plus, RefreshCw, Search, Send, Settings2,
  Sparkles, Tags, Trash2, WandSparkles, X,
} from 'lucide-react'
import { ApiFailure, errorText, type GenerationRequest } from './api'
import type { GenerationDraft } from './store'
import { AppStore, CHARACTER_POSITION_CENTER, MAX_CHARACTERS, NATIVE_CHARACTER_MODELS, supportsNativeCharacters } from './store'
import { CharacterPositions } from './CharacterPositions'
import { PromptEditor } from './PromptEditor'
import { StyleExperimentConfig, StyleExperimentProgress, StyleExperimentResults } from './StyleExperiment'

const SOURCE_URL = 'https://huggingface.co/spaces/SAkizuki/DanbooruSearch'
const RESOLUTION_PRESETS = [
  { id: 'small-portrait', tier: '小图', label: '竖图', width: '512', height: '768' },
  { id: 'small-square', tier: '小图', label: '方图', width: '640', height: '640' },
  { id: 'small-landscape', tier: '小图', label: '横图', width: '768', height: '512' },
  { id: 'portrait', tier: '标准', label: '竖图', width: '832', height: '1216' },
  { id: 'square', tier: '标准', label: '方图', width: '1024', height: '1024' },
  { id: 'landscape', tier: '标准', label: '横图', width: '1216', height: '832' },
  { id: 'large-portrait', tier: '大图', label: '竖图', width: '1024', height: '1536' },
  { id: 'large-square', tier: '大图', label: '方图', width: '1472', height: '1472' },
  { id: 'large-landscape', tier: '大图', label: '横图', width: '1536', height: '1024' },
] as const
const RESOLUTION_TIERS = ['小图', '标准', '大图'] as const
const SAMPLER_PRESETS = [
  { id: 'k_euler', label: 'Euler' },
  { id: 'k_euler_ancestral', label: 'Euler Ancestral' },
  { id: 'k_dpmpp_2s_ancestral', label: 'DPM++ 2S Ancestral' },
  { id: 'k_dpmpp_2m', label: 'DPM++ 2M' },
  { id: 'k_dpmpp_2m_sde', label: 'DPM++ 2M SDE' },
  { id: 'k_dpmpp_sde', label: 'DPM++ SDE' },
  { id: 'ddim_v3', label: 'DDIM' },
] as const
const PROMPT_TABS = [['positive', '正向'], ['negative', '负面']] as const
type PromptPanel = (typeof PROMPT_TABS)[number][0]

function Alert({ text }: { text: string }) {
  return text ? <p role="alert" className="alert">{text}</p> : null
}

const Login = observer(({ store }: { store: AppStore }) => {
  const tokenRef = useRef<HTMLInputElement>(null)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const token = tokenRef.current?.value.trim() ?? ''
    if (tokenRef.current) tokenRef.current.value = ''
    if (token) void store.auth.login(token)
  }

  return <main className="login-shell">
    <div className="login-brand"><ImageIcon size={24} aria-hidden="true" /> NovelAI 图像工作台</div>
    <form className="login-form" onSubmit={submit}>
      <h1>进入工作台</h1>
      <label htmlFor="access-token">访问令牌</label>
      <input id="access-token" ref={tokenRef} type="password" required autoComplete="off" spellCheck={false} autoCapitalize="off" />
      <Alert text={store.auth.error} />
      <button className="primary" type="submit" disabled={store.auth.status === 'loading'}>
        <LogOut className="login-icon" size={17} aria-hidden="true" />
        {store.auth.status === 'loading' ? '正在验证...' : '进入工作台'}
      </button>
    </form>
  </main>
})

function NumericField({ label, name, value, onChange, min, max, step = 1, placeholder }: {
  label: string
  name: keyof GenerationDraft
  value: string
  onChange: (name: keyof GenerationDraft, value: string) => void
  min: number
  max: number
  step?: number | 'any'
  placeholder?: string
}) {
  return <label className="field">
    <span>{label}</span>
    <input type="number" inputMode="decimal" value={value} min={min} max={max} step={step}
      placeholder={placeholder} onChange={event => onChange(name, event.target.value)} />
  </label>
}

const Editor = observer(({ store, onOpenSettings }: { store: AppStore; onOpenSettings: () => void }) => {
  const [panel, setPanel] = useState<PromptPanel>('positive')
  const [experimentOpen, setExperimentOpen] = useState(false)
  const generation = store.generation
  const draft = generation.draft
  const active = generation.operationLocked || generation.experimentRunning || generation.busy || generation.activeId !== null || generation.submitUncertain

  function onPromptTabKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const current = PROMPT_TABS.findIndex(([name]) => name === panel)
    const next = event.key === 'ArrowDown' ? (current + 1) % PROMPT_TABS.length
      : event.key === 'ArrowUp' ? (current + PROMPT_TABS.length - 1) % PROMPT_TABS.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? PROMPT_TABS.length - 1 : null
    if (next === null) return
    event.preventDefault()
    setPanel(PROMPT_TABS[next][0])
    event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus()
  }

  return <section className="editor" aria-labelledby="editor-title">
    <div className="section-heading">
      <div><span className="eyebrow">创作</span><h2 id="editor-title">图像生成</h2></div>
      <span className="section-meta">文生图</span>
    </div>
    <form onSubmit={event => { event.preventDefault(); void generation.submit() }}>
      <div className="prompt-composer">
        <div className="prompt-tabs" role="tablist" aria-label="提示词类型" aria-orientation="vertical" onKeyDown={onPromptTabKeyDown}>
          {PROMPT_TABS.map(([name, label]) => <button key={name} id={`prompt-tab-${name}`} type="button" role="tab"
            aria-selected={panel === name} aria-controls={`prompt-panel-${name}`} tabIndex={panel === name ? 0 : -1}
            className={panel === name ? 'prompt-tab active' : 'prompt-tab'} onClick={() => setPanel(name)}>{label}</button>)}
        </div>
        <div className="prompt-panel prompt-stack" id="prompt-panel-positive" role="tabpanel" aria-labelledby="prompt-tab-positive" hidden={panel !== 'positive'}>
          <div className="field prompt-field"><div className="style-prompt-heading"><label htmlFor="style-prompt">画风</label>
            <button className="text-action" type="button" aria-expanded={experimentOpen} aria-controls="style-experiment-config"
              onClick={() => setExperimentOpen(!experimentOpen)}><FlaskConical size={14} aria-hidden="true" /> 画风实验</button></div>
            <PromptEditor id="style-prompt" label="画风" value={draft.style_prompt} rows={2} placeholder="画风、媒介与画质标签"
              onFocus={() => generation.setPositiveTagTarget('style_prompt')}
              onChange={value => generation.setField('style_prompt', value)} />
            <StyleExperimentConfig generation={generation} hidden={!experimentOpen} /></div>
          <div className="field prompt-field"><label htmlFor="shared-prompt">公共</label>
            <PromptEditor id="shared-prompt" label="公共" value={draft.positive_prompt} rows={3} placeholder="描述场景、构图与人物共有内容"
              onFocus={() => generation.setPositiveTagTarget('positive_prompt')}
              onChange={value => generation.setField('positive_prompt', value)} /></div>
          <p className="prompt-hint">画风和公共至少填写一项，合计最多 3000 字符。</p>
          <section className="character-section" aria-labelledby="characters-title">
            <div className="character-heading"><h3 id="characters-title">人物 <span>{draft.character_prompts.length} / {MAX_CHARACTERS}</span></h3>
              <button className="text-action" id="add-character" type="button" disabled={draft.character_prompts.length >= MAX_CHARACTERS}
                onClick={() => {
                  const id = generation.addCharacter()
                  if (id) requestAnimationFrame(() => document.getElementById(`character-prompt-${id}`)?.focus())
                }}><Plus size={15} aria-hidden="true" /> 添加人物</button>
            </div>
            <p className="prompt-hint">分别填写每个人物的特征，拖动下方编号调整位置。留空的人物不会提交。</p>
            <CharacterPositions generation={generation} />
            <div className="character-list">{draft.character_prompts.map((character, index) => <div className="character-card" key={character.id}>
              <div className="character-card-heading"><label htmlFor={`character-prompt-${character.id}`}>人物 {index + 1}</label>
                <button className="icon-button danger" type="button" title={`移除人物 ${index + 1}`} aria-label={`移除人物 ${index + 1}`}
                  onClick={() => {
                    generation.removeCharacter(character.id)
                    requestAnimationFrame(() => document.getElementById('add-character')?.focus())
                  }}><X size={15} aria-hidden="true" /></button>
              </div>
              <div className="field"><PromptEditor id={`character-prompt-${character.id}`} label={`人物 ${index + 1}`} value={character.prompt} rows={2}
                placeholder="这个人物的外貌、服装、动作等"
                onFocus={() => generation.setPositiveTagTarget(`character:${character.id}`)}
                onChange={value => generation.setCharacterPrompt(character.id, value)} /></div>
            </div>)}</div>
          </section>
        </div>
        <div className="prompt-panel" id="prompt-panel-negative" role="tabpanel" aria-labelledby="prompt-tab-negative" hidden={panel !== 'negative'}>
          <div className="field prompt-field"><label htmlFor="negative-prompt">负面提示词</label>
            <PromptEditor id="negative-prompt" label="负面提示词" value={draft.negative_prompt} rows={8} placeholder="排除的内容，应用于整张图像"
              onChange={value => generation.setField('negative_prompt', value)} /></div>
        </div>
      </div>
      <p className="prompt-hint prompt-weight-compatibility">数字权重适用于 V4 及更新模型。</p>
      <div className="submit-row">
        <button className="settings-link" type="button" onClick={onOpenSettings} title="打开生成设置">
          <Settings2 size={16} aria-hidden="true" />
          <span>{draft.model || '选择模型'} · {draft.width}×{draft.height} · {draft.steps} 步</span>
        </button>
        {!generation.job && !generation.activeId && <Alert text={generation.error} />}
        <button className="primary" type="submit" disabled={active}>
          <WandSparkles size={17} aria-hidden="true" />{generation.experimentRunning ? '画风实验进行中' : generation.activeId ? '正在生成...' : generation.submitUncertain ? '待核对历史' : generation.busy ? '正在提交...' : '生成图像'}
        </button>
      </div>
    </form>
    <StyleExperimentProgress generation={generation} />
  </section>
})

function SidePanel({ id, title, hidden, onClose, children }: {
  id: string
  title: string
  hidden: boolean
  onClose: () => void
  children: ReactNode
}) {
  return <aside className="settings-panel" id={id} aria-label={title} hidden={hidden}>
    <div className="settings-header"><h2>{title}</h2>
      <button className="icon-button" type="button" title={`关闭${title}`} aria-label={`关闭${title}`} onClick={onClose}><X size={18} aria-hidden="true" /></button>
    </div>
    <div className="settings-scroll">{children}</div>
  </aside>
}

const SettingsPanel = observer(({ store, hidden, onClose }: { store: AppStore; hidden: boolean; onClose: () => void }) => {
  const [manualSampler, setManualSampler] = useState(false)
  const generation = store.generation
  const draft = generation.draft
  const setNumeric = (name: keyof GenerationDraft, value: string) => generation.setField(name, value)
  const selectedResolution = RESOLUTION_PRESETS.find(preset => preset.width === draft.width && preset.height === draft.height)
  const selectedSampler = SAMPLER_PRESETS.find(preset => preset.id === draft.sampler)
  const showManualSampler = manualSampler || (draft.sampler !== '' && !selectedSampler)

  return <SidePanel id="generation-settings" title="生成设置" hidden={hidden} onClose={onClose}>
      <section className="settings-section" aria-labelledby="model-settings-title">
        <h3 id="model-settings-title">模型与采样</h3>
        <label className="field"><span>模型 ID <span className="required">*</span></span>
          <input value={draft.model} maxLength={80} autoComplete="off" placeholder="输入模型 ID" list="native-character-models"
            onChange={event => generation.setField('model', event.target.value)} /></label>
        <datalist id="native-character-models">{NATIVE_CHARACTER_MODELS.map(model => <option key={model} value={model} />)}</datalist>
        <p className="prompt-hint">独立人物支持列表中的 V4 / V4.5 / V5 模型。</p>
        {draft.character_prompts.some(character => character.prompt.trim()) && draft.model.trim() && !supportsNativeCharacters(draft.model)
          && <p className="model-hint" role="status">当前模型不支持独立人物，请选择列表中的模型。</p>}
        <label className="field"><span>采样器 <span className="required">*</span></span>
          <select value={showManualSampler ? 'manual' : draft.sampler} onChange={event => {
            const value = event.target.value
            setManualSampler(value === 'manual')
            if (value !== 'manual') generation.setField('sampler', value)
          }}>
            <option value="" disabled>请选择采样器</option>
            {SAMPLER_PRESETS.map(preset => <option key={preset.id} value={preset.id}>{preset.label} · {preset.id}</option>)}
            <option value="manual">手动输入 ID</option>
          </select></label>
        {showManualSampler && <label className="field"><span>手动采样器 ID <span className="required">*</span></span>
          <input value={draft.sampler} maxLength={80} autoComplete="off" placeholder="输入采样器 ID"
            onChange={event => {
              setManualSampler(true)
              generation.setField('sampler', event.target.value)
            }} /></label>}
      </section>
      <section className="settings-section" aria-labelledby="canvas-settings-title">
        <h3 id="canvas-settings-title">画布</h3>
        <label className="field"><span>图像尺寸</span>
          <select value={selectedResolution?.id ?? 'history'} onChange={event => {
            const preset = RESOLUTION_PRESETS.find(option => option.id === event.target.value)
            if (preset) generation.setResolution(preset.width, preset.height)
          }}>
            {!selectedResolution && <option value="history" disabled>历史尺寸 · {draft.width}×{draft.height}</option>}
            {RESOLUTION_TIERS.map(tier => <optgroup key={tier} label={tier}>
              {RESOLUTION_PRESETS.filter(preset => preset.tier === tier).map(preset =>
                <option key={preset.id} value={preset.id}>{preset.label} · {preset.width}×{preset.height}</option>)}
            </optgroup>)}
          </select>
        </label>
      </section>
      <section className="settings-section" aria-labelledby="sampling-settings-title">
        <h3 id="sampling-settings-title">采样</h3>
        <div className="settings-grid">
          <NumericField label="步数" name="steps" value={draft.steps} min={1} max={50} onChange={setNumeric} />
          <NumericField label="CFG 系数" name="cfg_scale" value={draft.cfg_scale} min={0} max={20} step="any" onChange={setNumeric} />
          <NumericField label="种子" name="seed" value={draft.seed} min={1} max={4294967295} placeholder="随机" onChange={setNumeric} />
          <NumericField label="张数" name="sample_count" value={draft.sample_count} min={1} max={8} onChange={setNumeric} />
        </div>
        <label className="quality-toggle"><input type="checkbox" checked={draft.quality}
          onChange={event => generation.setField('quality', event.target.checked)} /><span>高质量预设</span></label>
      </section>
  </SidePanel>
})

function statusText(status: string): string {
  return { queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[status] ?? status
}

function PromptSummary({ parameters }: { parameters: Pick<GenerationRequest, 'style_prompt' | 'positive_prompt' | 'character_prompts'> }) {
  return <dl className="prompt-summary">
    {parameters.style_prompt && <div><dt>画风</dt><dd>{parameters.style_prompt}</dd></div>}
    {parameters.positive_prompt && <div><dt>公共</dt><dd>{parameters.positive_prompt}</dd></div>}
    {(parameters.character_prompts ?? []).map((character, index) =>
      <div key={index}><dt>人物 {index + 1}</dt><dd>{character.prompt}
        <span className="character-saved-position">位置 X {(character.x ?? CHARACTER_POSITION_CENTER).toFixed(2)} · Y {(character.y ?? CHARACTER_POSITION_CENTER).toFixed(2)}</span>
      </dd></div>)}
  </dl>
}

const Result = observer(({ store }: { store: AppStore }) => {
  const generation = store.generation
  const job = generation.job
  if (generation.experimentRunning && !job && !generation.activeId) return null
  if (job && generation.experiment?.results.some(result => result.job.id === job.id)) return null
  return <section className="result-section" aria-labelledby="result-title">
    <div className="section-heading">
      <div><span className="eyebrow">结果</span><h2 id="result-title">本次生成</h2></div>
      {job && !generation.experimentRunning && !generation.operationLocked && job.status !== 'queued' && job.status !== 'running' && <button type="button" className="icon-button" title="关闭结果" aria-label="关闭结果"
        onClick={() => generation.clearResult()}><Check size={18} /></button>}
    </div>
    {!job && !generation.activeId && !generation.checking && <div className="empty-result"><ImageIcon size={27} aria-hidden="true" /><span>暂无生成结果</span></div>}
    {generation.activeId && !job && <div className="pending-result"><span className="status status-queued">已提交</span><span>任务 ID：{generation.activeId}</span>
      {generation.error && <button className="secondary" type="button" onClick={() => void generation.refresh()}><RefreshCw size={15} /> 检查状态</button>}
    </div>}
    {job && <Alert text={generation.error} />}
    {job && <>
      <div className="job-line"><span className={`status status-${job.status}`} role="status">{statusText(job.status)}</span>
        <span>实际种子 <strong>{job.effective_seed}</strong></span>
        {(job.status === 'queued' || job.status === 'running') && <span className="progress-track" aria-label="正在生成"><span /></span>}
        {job.status === 'succeeded' && <span>{job.image_count} 张图像</span>}
      </div>
      <details className="result-parameters"><summary>本次生成参数</summary>
        <PromptSummary parameters={job.parameters} />
        {job.parameters.negative_prompt && <p>负向：{job.parameters.negative_prompt}</p>}
        <p>{job.parameters.model} · {job.parameters.width}×{job.parameters.height} · {job.parameters.sampler}</p>
        <p>{job.parameters.steps} 步 · CFG {job.parameters.cfg_scale} · 实际种子 {job.effective_seed} · {job.parameters.sample_count} 张 · {job.parameters.quality ? '高质量' : '标准质量'}</p>
      </details>
      {job.result_expires_at && <p className="subtle">服务端结果有效至 {new Date(job.result_expires_at * 1000).toLocaleString()}</p>}
      <Alert text={generation.imageError} />
      {(generation.error || generation.imageError) && <button className="secondary" type="button" onClick={() => void generation.refresh()}><RefreshCw size={15} /> 检查状态</button>}
      {generation.images.length > 0 && <div className="image-grid">{generation.images.map(image =>
        <figure key={image.url} className="image-item">
          <img src={image.url} alt={`生成图像 ${image.index + 1}`} />
          <figcaption><span>图像 {image.index + 1} · 种子 {job.effective_seed}</span>
            <a href={image.url} download={image.filename} className="icon-button" title={`下载图像 ${image.index + 1}`} aria-label={`下载图像 ${image.index + 1}`}><ArrowDownToLine size={17} /></a>
          </figcaption>
        </figure>)}</div>}
      {job.status === 'succeeded' && !generation.images.length && !generation.imageError && !generation.operationLocked && <p className="subtle">图像已过期，参数仍可在历史记录中查看。</p>}
    </>}
  </section>
})

const TagSearch = observer(({ store }: { store: AppStore }) => {
  const tags = store.tags
  const generation = store.generation
  const positiveTargetLabel = generation.positiveTagTargets.find(target => target.value === generation.positiveTagTarget)?.label ?? '公共'
  return <div className="tool-content">
    <form className="search-form" onSubmit={event => { event.preventDefault(); void tags.search() }}>
      <label className="sr-only" htmlFor="tag-query">搜索中文或英文标签</label>
      <input id="tag-query" value={tags.query} maxLength={100} placeholder="搜索中文或英文标签"
        onChange={event => tags.setQuery(event.target.value)} />
      <button className="primary icon-button" type="submit" title="搜索标签" aria-label="搜索标签"
        disabled={tags.loading || tags.retrySeconds > 0}><Search size={18} /></button>
    </form>
    <label className="field tag-target"><span>正向标签加入</span>
      <select value={generation.positiveTagTarget} onChange={event => generation.setPositiveTagTarget(event.target.value)}>
        {generation.positiveTagTargets.map(target => <option key={target.value} value={target.value}>{target.label}</option>)}
      </select>
    </label>
    <div className="source-line">来源：<a href={SOURCE_URL} target="_blank" rel="noopener noreferrer">DanbooruSearch</a></div>
    <Alert text={tags.error} />
    {tags.retrySeconds > 0 && <p className="subtle" role="status">{tags.retrySeconds} 秒后可重试</p>}
    {tags.loading && <p className="subtle" role="status">正在搜索...</p>}
    {tags.searched && tags.results.length === 0 && <p className="subtle">没有匹配的标签</p>}
    <div className="tag-results">{tags.results.map((candidate, index) => <article className="tag-item" key={`${candidate.tag}-${index}`}>
      <div className="tag-head"><strong>{candidate.tag}</strong>{candidate.is_nsfw === true && <span className="nsfw">NSFW</span>}</div>
      {candidate.cn_name && <div className="tag-cn">{candidate.cn_name}</div>}
      {(candidate.category || candidate.count != null || candidate.score != null) && <div className="tag-meta">
        {candidate.category && <span>{candidate.category}</span>}
        {candidate.count != null && <span>{candidate.count.toLocaleString()} 次使用</span>}
        {candidate.score != null && <span>评分 {candidate.score.toFixed(2)}</span>}
      </div>}
      {candidate.summary && <p className="tag-summary">{candidate.summary}</p>}
      <div className="tag-actions">
        <button type="button" className="text-action" title={`将 ${candidate.tag} 加入${positiveTargetLabel}`} aria-label={`将 ${candidate.tag} 加入${positiveTargetLabel}`}
          onClick={() => generation.insertTag(candidate.tag, 'positive')}>+ {positiveTargetLabel}</button>
        <button type="button" className="text-action" title={`将 ${candidate.tag} 加入负面提示词`} aria-label={`将 ${candidate.tag} 加入负面提示词`}
          onClick={() => generation.insertTag(candidate.tag, 'negative')}>+ 负面</button>
      </div>
    </article>)}</div>
  </div>
})

const Advice = observer(({ store }: { store: AppStore }) => {
  const advice = store.advice
  return <div className="tool-content">
    <form onSubmit={event => { event.preventDefault(); void advice.submit() }}>
      <label className="field" htmlFor="advice-input"><span>咨询内容</span>
        <textarea id="advice-input" value={advice.input} maxLength={4000} rows={6}
          placeholder="输入提示词或参数问题" onChange={event => advice.setInput(event.target.value)} /></label>
      <div className="tool-submit"><button className="primary" type="submit" disabled={advice.loading}><Send size={16} />{advice.loading ? '正在等待...' : '获取建议'}</button></div>
    </form>
    <Alert text={advice.error} />
    {advice.output && <div className="advice-output" aria-label="建议结果"><h3>建议</h3><p>{advice.output}</p></div>}
  </div>
})

const HistoryPanel = observer(({ store }: { store: AppStore }) => {
  const history = store.history
  return <div className="tool-content">
    <div className="history-toolbar"><span>已保存的参数</span>
      <button type="button" className="icon-button" title="刷新历史" aria-label="刷新历史"
        onClick={() => void history.load()} disabled={history.loading || history.deletingId !== null}><RefreshCw size={17} /></button></div>
    <Alert text={history.error} />
    {history.loading && <p className="subtle" role="status">正在加载历史...</p>}
    {!history.loading && !history.error && history.items.length === 0 && <p className="subtle">暂无历史记录</p>}
    <div className="history-list">{history.items.map(item => <article className="history-item" key={item.id}>
      <div className="history-top"><time dateTime={new Date(item.created_at * 1000).toISOString()}>{new Date(item.created_at * 1000).toLocaleString()}</time><span className={`status status-${item.status}`}>{statusText(item.status)}</span></div>
      <PromptSummary parameters={item.parameters} />
      {item.parameters.negative_prompt && <p className="history-negative">排除：{item.parameters.negative_prompt}</p>}
      <div className="history-meta">{item.parameters.model} · {item.parameters.width}×{item.parameters.height} · 种子 {item.effective_seed}</div>
      <div className="history-meta">{item.parameters.sampler} · {item.parameters.steps} 步 · CFG {item.parameters.cfg_scale} · {item.parameters.sample_count} 张 · {item.parameters.quality ? '高质量' : '标准质量'}</div>
      {item.error_code && <p className="history-negative">{errorText(new ApiFailure(0, item.error_code, '生成失败，请检查服务状态。'))}</p>}
      <div className="history-actions">
        <button className="text-action" type="button" onClick={() => { store.generation.reuse(item); document.getElementById('editor-title')?.scrollIntoView({ behavior: 'smooth' }) }}><History size={15} /> 复用</button>
        {(item.status === 'queued' || item.status === 'running') && <button className="text-action" type="button"
          disabled={store.generation.experimentRunning || store.generation.operationLocked || store.generation.activeId !== null || store.generation.busy || store.generation.submitUncertain}
          onClick={() => { store.generation.resume(item.id); document.getElementById('result-title')?.scrollIntoView({ behavior: 'smooth' }) }}><RefreshCw size={15} /> 查看状态</button>}
        <button className="icon-button danger" type="button" title={item.status === 'queued' || item.status === 'running' ? '任务完成后可删除' : '删除历史记录'} aria-label={`删除 ${new Date(item.created_at * 1000).toLocaleString()} 的历史记录`}
          disabled={history.deletingId !== null || item.status === 'queued' || item.status === 'running'} onClick={() => {
            if (window.confirm('确定删除这条参数记录？此操作无法撤销。')) void history.delete(item.id)
          }}><Trash2 size={16} /></button>
      </div>
    </article>)}</div>
    <div className="pager">
      <button className="icon-button" type="button" title="上一页历史" aria-label="上一页历史" disabled={history.loading || history.deletingId !== null || history.offset === 0}
        onClick={() => void history.load(Math.max(0, history.offset - 20))}><ArrowLeft size={18} /></button>
      <span>第 {Math.floor(history.offset / 20) + 1} 页</span>
      <button className="icon-button" type="button" title="下一页历史" aria-label="下一页历史" disabled={history.loading || history.deletingId !== null || history.nextOffset === null}
        onClick={() => { if (history.nextOffset !== null) void history.load(history.nextOffset) }}><ArrowRight size={18} /></button>
    </div>
  </div>
})

const LEFT_PANELS = [
  { name: 'settings', id: 'generation-settings', Icon: Settings2, label: '生成设置' },
  { name: 'history', id: 'workspace-history', Icon: History, label: '历史记录' },
  { name: 'tags', id: 'workspace-tags', Icon: Tags, label: '提示词查询' },
  { name: 'advice', id: 'workspace-advice', Icon: Sparkles, label: 'AI 建议' },
] as const
type Panel = (typeof LEFT_PANELS)[number]['name']

const Workspace = observer(({ store }: { store: AppStore }) => {
  const [activePanel, setActivePanel] = useState<Panel | null>(() =>
    typeof window !== 'undefined' && window.matchMedia('(min-width: 901px)').matches ? 'settings' : null)
  useEffect(() => { void store.enterWorkspace() }, [store])

  function closePanel() {
    if (activePanel === null) return
    document.getElementById(`panel-toggle-${activePanel}`)?.focus()
    setActivePanel(null)
  }

  function openPanel(name: Panel) {
    const previous = LEFT_PANELS.find(panel => panel.name === activePanel)
    if (previous && previous.name !== name && document.getElementById(previous.id)?.contains(document.activeElement)) {
      document.getElementById(`panel-toggle-${name}`)?.focus()
    }
    setActivePanel(name)
  }

  const activePanelLabel = LEFT_PANELS.find(panel => panel.name === activePanel)?.label

  return <div className="app-shell" onKeyDown={event => {
    if (event.key === 'Escape' && !event.defaultPrevented && activePanel !== null) {
      event.preventDefault()
      closePanel()
    }
  }}>
    <header className="app-header"><div className="brand"><ImageIcon size={21} aria-hidden="true" /><span>NovelAI</span><span className="brand-sub">图像工作台</span></div>
      <div className="header-actions"><span className="user-label">{store.auth.user?.label}</span>
        <button className="icon-button" type="button" title="退出登录" aria-label="退出登录" disabled={store.auth.loggingOut}
          onClick={() => void store.auth.logout()}><LogOut size={19} /></button></div>
    </header>
    {store.auth.error && <div className="auth-alert"><Alert text={store.auth.error} /></div>}
    <main className="workspace-body">
      <nav className="side-rail" aria-label="工作台导航">
        {LEFT_PANELS.map(({ name, id, Icon, label }) => <button key={name} id={`panel-toggle-${name}`}
          className={activePanel === name ? 'rail-button active' : 'rail-button'} type="button" title={label} aria-label={label}
          aria-expanded={activePanel === name} aria-controls={id} onClick={() => activePanel === name ? closePanel() : openPanel(name)}>
          <Icon size={19} aria-hidden="true" /><span className="rail-label">{label}</span>
        </button>)}
      </nav>
      {activePanel !== null && <button className="settings-scrim" type="button" aria-label={`关闭${activePanelLabel}`} onClick={closePanel} />}
      <SettingsPanel store={store} hidden={activePanel !== 'settings'} onClose={closePanel} />
      {LEFT_PANELS.filter(panel => panel.name !== 'settings').map(({ name, id, label }) =>
        <SidePanel key={name} id={id} title={label} hidden={activePanel !== name} onClose={closePanel}>
          {name === 'history' ? <HistoryPanel store={store} /> : name === 'tags' ? <TagSearch store={store} /> : <Advice store={store} />}
        </SidePanel>)}
      <div className="main-column">
        <div className="main-scroll"><Editor store={store} onOpenSettings={() => openPanel('settings')} />
          <StyleExperimentResults generation={store.generation} /><Result store={store} /></div>
        {store.generation.submitUncertain && <div className="uncertain-bar" role="alert">
          <span>提交结果未知，请核对历史记录。</span>
          <button className="secondary" type="button" onClick={() => { openPanel('history'); void store.history.load(0) }}>查看历史</button>
          <button className="secondary" type="button" onClick={() => store.generation.acknowledgeUncertain()}>核对后继续</button>
        </div>}
      </div>
    </main>
  </div>
})

export const App = observer(({ store }: { store: AppStore }) => {
  useEffect(() => { void store.auth.restore(); return () => store.dispose() }, [store])
  if (store.auth.loggingOut) return <div className="loading-screen" role="status">正在退出...</div>
  if (store.auth.status === 'checking') return <div className="loading-screen" role="status">正在恢复会话...</div>
  if (store.auth.status === 'error') return <div className="loading-screen"><Alert text={store.auth.error} /><button className="secondary" onClick={() => void store.auth.restore()}><RefreshCw size={16} /> 重试</button></div>
  if (store.auth.status !== 'ready') return <Login store={store} />
  return <Workspace store={store} />
})
