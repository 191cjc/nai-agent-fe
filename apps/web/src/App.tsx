import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { observer } from 'mobx-react-lite'
import {
  ArrowDownToLine, ArrowLeft, ArrowRight, Check, ChevronDown, ChevronUp, Clock3,
  History, Image as ImageIcon, LogOut, RefreshCw, Search, Send, Settings2,
  Sparkles, Tags, Trash2, WandSparkles, X,
} from 'lucide-react'
import { ApiFailure, errorText } from './api'
import type { GenerationDraft } from './store'
import { AppStore } from './store'

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
  const generation = store.generation
  const draft = generation.draft
  const active = generation.busy || generation.activeId !== null || generation.submitUncertain

  return <section className="editor" aria-labelledby="editor-title">
    <div className="section-heading">
      <div><span className="eyebrow">创作</span><h2 id="editor-title">图像生成</h2></div>
      <span className="section-meta">文生图</span>
    </div>
    <form onSubmit={event => { event.preventDefault(); void generation.submit() }}>
      <div className="prompt-stack">
        <label className="field prompt-field"><span>正向提示词 <span className="required">*</span></span>
          <textarea value={draft.positive_prompt} maxLength={3000} rows={5} placeholder="描述画面"
            onChange={event => generation.setField('positive_prompt', event.target.value)} /></label>
        <label className="field prompt-field"><span>负向提示词</span>
          <textarea value={draft.negative_prompt} maxLength={3000} rows={3} placeholder="排除的内容"
            onChange={event => generation.setField('negative_prompt', event.target.value)} /></label>
      </div>
      <div className="submit-row">
        <button className="settings-link" type="button" onClick={onOpenSettings} title="打开生成设置">
          <Settings2 size={16} aria-hidden="true" />
          <span>{draft.model || '选择模型'} · {draft.width}×{draft.height} · {draft.steps} 步</span>
        </button>
        {!generation.job && !generation.activeId && <Alert text={generation.error} />}
        <button className="primary" type="submit" disabled={active}>
          <WandSparkles size={17} aria-hidden="true" />{generation.activeId ? '正在生成...' : generation.submitUncertain ? '待核对历史' : generation.busy ? '正在提交...' : '生成图像'}
        </button>
      </div>
    </form>
  </section>
})

const SettingsPanel = observer(({ store, hidden, onClose }: { store: AppStore; hidden: boolean; onClose: () => void }) => {
  const generation = store.generation
  const draft = generation.draft
  const setNumeric = (name: keyof GenerationDraft, value: string) => generation.setField(name, value)
  const selectedResolution = RESOLUTION_PRESETS.find(preset => preset.width === draft.width && preset.height === draft.height)

  return <aside className="settings-panel" id="generation-settings" aria-label="生成设置" hidden={hidden}>
    <div className="settings-header"><h2>生成设置</h2>
      <button className="icon-button" type="button" title="关闭生成设置" aria-label="关闭生成设置" onClick={onClose}><X size={18} /></button>
    </div>
    <div className="settings-scroll">
      <section className="settings-section" aria-labelledby="model-settings-title">
        <h3 id="model-settings-title">模型与采样</h3>
        <label className="field"><span>模型 ID <span className="required">*</span></span>
          <input value={draft.model} maxLength={80} autoComplete="off" placeholder="输入模型 ID"
            onChange={event => generation.setField('model', event.target.value)} /></label>
        <label className="field"><span>采样器 ID <span className="required">*</span></span>
          <input value={draft.sampler} maxLength={80} autoComplete="off" placeholder="输入采样器 ID"
            onChange={event => generation.setField('sampler', event.target.value)} /></label>
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
    </div>
  </aside>
})

function statusText(status: string): string {
  return { queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[status] ?? status
}

const Result = observer(({ store }: { store: AppStore }) => {
  const generation = store.generation
  const job = generation.job
  return <section className="result-section" aria-labelledby="result-title">
    <div className="section-heading">
      <div><span className="eyebrow">结果</span><h2 id="result-title">本次生成</h2></div>
      {job && job.status !== 'queued' && job.status !== 'running' && <button type="button" className="icon-button" title="关闭结果" aria-label="关闭结果"
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
        <p>正向：{job.parameters.positive_prompt}</p>
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
      {job.status === 'succeeded' && !generation.images.length && !generation.imageError && <p className="subtle">图像已过期，参数仍可在历史记录中查看。</p>}
    </>}
  </section>
})

const TagSearch = observer(({ store }: { store: AppStore }) => {
  const tags = store.tags
  return <div className="tool-content">
    <form className="search-form" onSubmit={event => { event.preventDefault(); void tags.search() }}>
      <label className="sr-only" htmlFor="tag-query">搜索中文或英文标签</label>
      <input id="tag-query" value={tags.query} maxLength={100} placeholder="搜索中文或英文标签"
        onChange={event => tags.setQuery(event.target.value)} />
      <button className="primary icon-button" type="submit" title="搜索标签" aria-label="搜索标签"
        disabled={tags.loading || tags.retrySeconds > 0}><Search size={18} /></button>
    </form>
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
        <button type="button" className="text-action" title={`将 ${candidate.tag} 加入正向提示词`} aria-label={`将 ${candidate.tag} 加入正向提示词`}
          onClick={() => store.generation.insertTag(candidate.tag, 'positive_prompt')}>+ 正向</button>
        <button type="button" className="text-action" title={`将 ${candidate.tag} 加入负向提示词`} aria-label={`将 ${candidate.tag} 加入负向提示词`}
          onClick={() => store.generation.insertTag(candidate.tag, 'negative_prompt')}>+ 负向</button>
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
      <p className="history-prompt">{item.parameters.positive_prompt}</p>
      {item.parameters.negative_prompt && <p className="history-negative">排除：{item.parameters.negative_prompt}</p>}
      <div className="history-meta">{item.parameters.model} · {item.parameters.width}×{item.parameters.height} · 种子 {item.effective_seed}</div>
      <div className="history-meta">{item.parameters.sampler} · {item.parameters.steps} 步 · CFG {item.parameters.cfg_scale} · {item.parameters.sample_count} 张 · {item.parameters.quality ? '高质量' : '标准质量'}</div>
      {item.error_code && <p className="history-negative">{errorText(new ApiFailure(0, item.error_code, '生成失败，请检查服务状态。'))}</p>}
      <div className="history-actions">
        <button className="text-action" type="button" onClick={() => { store.generation.reuse(item); document.getElementById('editor-title')?.scrollIntoView({ behavior: 'smooth' }) }}><History size={15} /> 复用</button>
        {(item.status === 'queued' || item.status === 'running') && <button className="text-action" type="button" disabled={store.generation.activeId !== null}
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

type Tool = 'tags' | 'advice' | 'history'

const Workspace = observer(({ store }: { store: AppStore }) => {
  const [tool, setTool] = useState<Tool>('history')
  const [drawerOpen, setDrawerOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(() => typeof window !== 'undefined' && window.matchMedia('(min-width: 901px)').matches)
  useEffect(() => { void store.history.load(0) }, [store])
  useEffect(() => {
    function closeSettings(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') setSettingsOpen(false)
    }
    window.addEventListener('keydown', closeSettings)
    return () => window.removeEventListener('keydown', closeSettings)
  }, [])

  function openTool(name: Tool) {
    setTool(name)
    setDrawerOpen(true)
  }

  function onTabKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const order: Tool[] = ['tags', 'advice', 'history']
    const current = order.indexOf(tool)
    const next = event.key === 'ArrowRight' ? (current + 1) % order.length
      : event.key === 'ArrowLeft' ? (current + order.length - 1) % order.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? order.length - 1 : null
    if (next === null) return
    event.preventDefault()
    openTool(order[next])
    event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus()
  }

  return <div className="app-shell">
    <header className="app-header"><div className="brand"><ImageIcon size={21} aria-hidden="true" /><span>NovelAI</span><span className="brand-sub">图像工作台</span></div>
      <div className="header-actions"><span className="user-label">{store.auth.user?.label}</span>
        <button className="icon-button" type="button" title="退出登录" aria-label="退出登录" disabled={store.auth.loggingOut}
          onClick={() => void store.auth.logout()}><LogOut size={19} /></button></div>
    </header>
    {store.auth.error && <div className="auth-alert"><Alert text={store.auth.error} /></div>}
    <main className="workspace-body">
      <nav className="side-rail" aria-label="工作台导航">
        <button className={settingsOpen ? 'rail-button active' : 'rail-button'} type="button" title="生成设置" aria-label="生成设置"
          aria-expanded={settingsOpen} aria-controls="generation-settings" onClick={() => setSettingsOpen(!settingsOpen)}><Settings2 size={21} /></button>
        <span className="rail-divider" aria-hidden="true" />
        <button className={drawerOpen && tool === 'tags' ? 'rail-button active' : 'rail-button'} type="button" title="标签搜索" aria-label="标签搜索"
          onClick={() => openTool('tags')}><Tags size={20} /></button>
        <button className={drawerOpen && tool === 'advice' ? 'rail-button active' : 'rail-button'} type="button" title="建议" aria-label="建议"
          onClick={() => openTool('advice')}><Sparkles size={20} /></button>
        <button className={drawerOpen && tool === 'history' ? 'rail-button active' : 'rail-button'} type="button" title="历史记录" aria-label="历史记录"
          onClick={() => openTool('history')}><History size={20} /></button>
      </nav>
      {settingsOpen && <button className="settings-scrim" type="button" aria-label="关闭生成设置" onClick={() => setSettingsOpen(false)} />}
      <SettingsPanel store={store} hidden={!settingsOpen} onClose={() => setSettingsOpen(false)} />
      <div className="main-column">
        <div className="main-scroll"><Editor store={store} onOpenSettings={() => setSettingsOpen(true)} /><Result store={store} /></div>
        {store.generation.submitUncertain && <div className="uncertain-bar" role="alert">
          <span>提交结果未知，请核对历史记录。</span>
          <button className="secondary" type="button" onClick={() => { openTool('history'); void store.history.load(0) }}>查看历史</button>
          <button className="secondary" type="button" onClick={() => store.generation.acknowledgeUncertain()}>核对后继续</button>
        </div>}
        <section className={drawerOpen ? 'workspace-drawer open' : 'workspace-drawer'} aria-label="工作台抽屉">
          <div className="drawer-header">
            <div className="tool-tabs" role="tablist" aria-label="工作台工具" onKeyDown={onTabKeyDown}>
              {([['history', Clock3, '历史'], ['tags', Tags, '标签'], ['advice', Sparkles, '建议']] as const).map(([name, Icon, label]) =>
                <button key={name} type="button" role="tab" aria-selected={tool === name} aria-controls="drawer-panel"
                  tabIndex={tool === name ? 0 : -1} className={tool === name ? 'tool-tab active' : 'tool-tab'} onClick={() => openTool(name)}><Icon size={16} /><span>{label}</span></button>)}
            </div>
            <button className="icon-button drawer-toggle" type="button" title={drawerOpen ? '收起抽屉' : '展开抽屉'}
              aria-label={drawerOpen ? '收起抽屉' : '展开抽屉'} aria-expanded={drawerOpen} aria-controls="drawer-panel"
              onClick={() => setDrawerOpen(!drawerOpen)}>{drawerOpen ? <ChevronDown size={19} /> : <ChevronUp size={19} />}</button>
          </div>
          <div className="drawer-panel" id="drawer-panel" role="tabpanel" aria-label={tool === 'tags' ? '标签搜索' : tool === 'advice' ? '建议' : '历史'} hidden={!drawerOpen}>
            {tool === 'tags' ? <TagSearch store={store} /> : tool === 'advice' ? <Advice store={store} /> : <HistoryPanel store={store} />}
          </div>
        </section>
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
