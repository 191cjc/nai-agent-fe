import { useEffect, useRef, useState } from 'react'
import { observer } from 'mobx-react-lite'
import { Download, Layers, Plus, RotateCcw, Trash2, X } from 'lucide-react'
import { ApiFailure, errorText, type WorkspaceApi } from './api'
import { DATASET_CATEGORIES } from './dataset-prompts'
import { CUSTOM_CATEGORY, MAX_DATASET_ITEMS, MAX_DATASET_PROMPT_LENGTH, datasetItems, defaultDatasetEntries, nextCustomId, type DatasetEntry } from './dataset-run'
import { buildDatasetZip, downloadZip, experimentJobs, selectedJobs, type DatasetExportProgress } from './dataset-export'
import type { GenerationStore } from './store'

const CATEGORIES = [...DATASET_CATEGORIES, { id: CUSTOM_CATEGORY, label: '自定义', description: '手动添加的提示词' }]

function validationError(entries: readonly DatasetEntry[], style: string): string {
  try {
    datasetItems(entries, style)
    return ''
  } catch (error) {
    return error instanceof Error ? error.message : '训练集提示词无效。'
  }
}

export const DatasetRunConfig = observer(({ generation, hidden }: { generation: GenerationStore; hidden: boolean }) => {
  const [entries, setEntries] = useState<DatasetEntry[]>(defaultDatasetEntries)
  const [custom, setCustom] = useState('')
  const runs = generation.runs
  const snapshot = runs.kind === 'dataset' ? runs.snapshot : null
  const style = generation.draft.style_prompt
  const selected = entries.filter(entry => entry.selected)
  const samples = /^\d+$/.test(generation.draft.sample_count) ? Number(generation.draft.sample_count) : null
  const error = selected.length ? validationError(entries, style) : ''
  const locked = generation.operationLocked || generation.activeId !== null || generation.busy || generation.submitUncertain

  function update(id: string, change: Partial<DatasetEntry>) {
    setEntries(current => current.map(entry => entry.id === id ? { ...entry, ...change } : entry))
  }

  function selectCategory(category: string, value: boolean) {
    setEntries(current => current.map(entry => entry.category === category ? { ...entry, selected: value } : entry))
  }

  function addCustom() {
    const prompt = custom.trim()
    if (!prompt) return
    setEntries(current => [...current, { id: nextCustomId(current), category: CUSTOM_CATEGORY, prompt, selected: true }])
    setCustom('')
  }

  function start() {
    if (locked || error || !selected.length) return
    void generation.startDatasetRun(entries)
  }

  return <section id="dataset-run-config" className="style-experiment-config dataset-run-config" aria-labelledby="dataset-run-config-title" hidden={hidden}
    onKeyDown={event => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
    <h3 id="dataset-run-config-title"><Layers size={15} aria-hidden="true" /> 训练集批跑</h3>
    <p className="prompt-hint">用当前「画风」固定风格，逐条运行下面的内容提示词，生成用于训练画风 LoRA 的图片。提示词只描述内容，不含画风与质量词；导出时作为 caption。</p>
    <p className="prompt-hint">公共分区和人物卡片不参与批跑；负面提示词、模型、尺寸、步数、CFG、采样器和每条张数取自当前生成设置。</p>
    {snapshot ? <div className="experiment-note" role="status">
      <p>这里展示本次训练集批跑固定的画风与 {snapshot.items?.length ?? 0} 条提示词。编辑草稿不会改变服务器批跑。</p>
      <p>画风：{snapshot.parameters.style_prompt}</p>
    </div> : <>
      <div className="dataset-style-preview"><span>将应用的画风</span>
        <p>{style.trim() ? style : '（未填写画风）'}</p></div>
      <fieldset className="dataset-categories">
        <legend>按分类选择</legend>
        {CATEGORIES.map(category => {
          const members = entries.filter(entry => entry.category === category.id)
          if (!members.length) return null
          const count = members.filter(entry => entry.selected).length
          return <details className="dataset-category" key={category.id}>
            <summary>
              <input type="checkbox" checked={count === members.length} aria-label={`选择全部「${category.label}」`}
                ref={input => { if (input) input.indeterminate = count > 0 && count < members.length }}
                onClick={event => event.stopPropagation()} onChange={event => selectCategory(category.id, event.target.checked)} />
              <strong>{category.label}</strong><span>{count} / {members.length}</span>
              <span className="prompt-hint">{category.description}</span>
            </summary>
            <ul className="dataset-items">{members.map(entry => <li key={entry.id} className={entry.selected ? '' : 'muted'}>
              <input type="checkbox" checked={entry.selected} aria-label={`选择提示词 ${entry.id}`}
                onChange={event => update(entry.id, { selected: event.target.checked })} />
              <input type="text" value={entry.prompt} maxLength={MAX_DATASET_PROMPT_LENGTH} spellCheck={false} aria-label={`编辑提示词 ${entry.id}`}
                onChange={event => update(entry.id, { prompt: event.target.value })} />
              <button className="icon-button" type="button" title="移除这条提示词" aria-label={`移除提示词 ${entry.id}`}
                onClick={() => setEntries(current => current.filter(item => item.id !== entry.id))}><Trash2 size={14} /></button>
            </li>)}</ul>
          </details>
        })}
      </fieldset>
      <div className="dataset-custom">
        <input type="text" value={custom} maxLength={MAX_DATASET_PROMPT_LENGTH} spellCheck={false} placeholder="添加自定义内容提示词，例如 1girl, solo, sitting, library"
          aria-label="自定义提示词" onChange={event => setCustom(event.target.value)}
          onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); addCustom() } }} />
        <button className="secondary" type="button" disabled={!custom.trim()} onClick={addCustom}><Plus size={14} aria-hidden="true" /> 添加</button>
        <button className="text-action" type="button" onClick={() => { if (window.confirm('恢复为内置提示词库？自定义和编辑内容将丢失。')) setEntries(defaultDatasetEntries()) }}>
          <RotateCcw size={14} aria-hidden="true" /> 恢复默认</button>
      </div>
    </>}
    {!snapshot && error && <p className="alert" role="alert">{error}</p>}
    {!snapshot && <div className="experiment-preview" aria-live="polite" aria-atomic="true">
      <p><strong>{selected.length} 条</strong>{samples !== null && samples >= 1 && samples <= 8 && <> × 每条 {samples} 张 = <strong>{selected.length * samples} 张图像</strong></>}
        {selected.length > MAX_DATASET_ITEMS && `（上限 ${MAX_DATASET_ITEMS} 条）`}</p>
      <p className="prompt-hint">每条提示词是一次付费生成。画风 LoRA 一般 30–150 张精选图即可。</p>
    </div>}
    <p className="prompt-hint">每条使用不同种子：生成设置中的种子作为基础种子（留空则服务器随机一次），第 N 条使用基础种子 + N − 1，便于复现。</p>
    <p className="prompt-hint">批跑在服务器依次执行，单条失败后继续下一条，不会自动重试。刷新、关闭页面或退出登录不会停止；只有“停止实验”会阻止后续条目。与画风实验共用“同时只能运行一个”的限制。</p>
    <p className="prompt-hint">图片私有保存 7 天，请在过期前从历史记录的「画风实验」中导出训练集。</p>
    {!snapshot && generation.error && !generation.submitUncertain && <p className="alert" role="alert">{generation.error}</p>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={locked || Boolean(error) || !selected.length || selected.length > MAX_DATASET_ITEMS} onClick={start}>
        <Layers size={15} aria-hidden="true" /> 开始批跑
      </button>
    </div>
  </section>
})

export type DatasetExportSource = { kind: 'experiment'; id: string } | { kind: 'selection'; ids: readonly string[] }

export function DatasetExportPanel({ api, source, onClose }: { api: WorkspaceApi; source: DatasetExportSource; onClose: () => void }) {
  const [trigger, setTrigger] = useState('')
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<DatasetExportProgress | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function run() {
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setRunning(true)
    setError('')
    setMessage('')
    setProgress(null)
    try {
      const jobs = source.kind === 'experiment'
        ? await experimentJobs(api, source.id, current.signal)
        : await selectedJobs(api, source.ids, current.signal)
      const result = await buildDatasetZip(api, jobs, trigger, current.signal, setProgress)
      if (current.signal.aborted) return
      if (!result.blob) setError(`没有可导出的图片（跳过 ${result.skipped} 张：失败、已过期或不可用）。`)
      else {
        downloadZip(result.blob, `lora-dataset-${new Date().toISOString().slice(0, 10)}.zip`)
        setMessage(`已导出 ${result.written} 张图片和对应 caption${result.skipped ? `，跳过 ${result.skipped} 张（失败、已过期或不可用）` : ''}。`)
      }
    } catch (exception) {
      if (!current.signal.aborted) setError(exception instanceof ApiFailure ? errorText(exception) : exception instanceof Error ? exception.message : '导出失败，请重试。')
      else setMessage('已取消导出。')
    } finally {
      if (controller.current === current) {
        controller.current = null
        setRunning(false)
      }
    }
  }

  return <div className="dataset-export" role="group" aria-label="导出训练集">
    <label className="field"><span>触发词（可选，加在每个 caption 开头）</span>
      <input type="text" value={trigger} maxLength={100} spellCheck={false} disabled={running} placeholder="例如 mystyle"
        onChange={event => setTrigger(event.target.value)} /></label>
    <p className="prompt-hint">zip 内为 0001.png + 0001.txt 成对文件。图片去除元数据与隐写信息；caption 只含内容提示词，不含画风。导出只读取已保存图片，不会生成。</p>
    {progress && <p role="status" aria-live="polite">已处理 {progress.processedJobs} / {progress.totalJobs} 条记录 · 已写入 {progress.written} 张 · 跳过 {progress.skipped} 张</p>}
    {message && <p className="experiment-note" role="status">{message}</p>}
    {error && <p className="alert" role="alert">{error}</p>}
    <div className="experiment-config-actions">
      {running
        ? <button className="secondary" type="button" onClick={() => controller.current?.abort()}><X size={14} aria-hidden="true" /> 取消导出</button>
        : <button className="primary" type="button" onClick={() => void run()}><Download size={14} aria-hidden="true" /> 导出 zip</button>}
      <button className="text-action" type="button" disabled={running} onClick={onClose}>关闭</button>
    </div>
  </div>
}
