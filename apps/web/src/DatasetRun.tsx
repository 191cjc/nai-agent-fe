import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { observer } from 'mobx-react-lite'
import { Download, Layers, Plus, RotateCcw, Trash2, UserRound, X } from 'lucide-react'
import { ApiFailure, errorText, type GenerationView, type WorkspaceApi } from './api'
import { DATASET_CATEGORIES, type DatasetCategory } from './dataset-prompts'
import { CHARACTER_CATEGORIES } from './character-prompts'
import { CUSTOM_CATEGORY, MAX_DATASET_ITEMS, MAX_DATASET_PROMPT_LENGTH, datasetItems, nextCustomId, type DatasetEntry } from './dataset-run'
import { defaultCharacterEntries, defaultDatasetEntries } from './dataset-defaults'
import { ANIMAGINE_QUALITY_PREFIX, buildDatasetZip, downloadZip, experimentJobs, selectedJobs, type DatasetExportProgress } from './dataset-export'
import { CharacterRunSettings, characterSnapshotSummary, useCharacterSettings } from './CharacterDataset'
import type { GenerationStore } from './store'

const CUSTOM: DatasetCategory = { id: CUSTOM_CATEGORY, label: '自定义', description: '手动添加的提示词' }

// Body-shape and suggestive tags must never be applied to child subjects.
const CHILD_UNSAFE_STYLE = /\b(soft body|supple skin|soft curves|curvy|curvaceous|cleavage|breasts?|skin folds|skin compression|thick thighs|wide hips|sexy|seductive|sensual|erotic|nsfw|lewd|plump|voluptuous|navel|midriff|bare shoulders|thighs)\b/i

function childSafetyError(entries: readonly DatasetEntry[], style: string): string {
  if (!entries.some(entry => entry.selected && entry.category === 'boy')) return ''
  const match = style.match(CHILD_UNSAFE_STYLE)
  return match
    ? `已选「男孩（年幼）」条目，但画风中含有身体描写类标签「${match[0]}」。这类标签绝不能用于年幼角色：请取消男孩条目，或改用去掉身体描写的画风单独批跑。`
    : ''
}

function validationError(entries: readonly DatasetEntry[], styles: readonly string[], traits?: string): string {
  try {
    datasetItems(entries, styles, traits)
    return ''
  } catch (error) {
    return error instanceof Error ? error.message : '训练集提示词无效。'
  }
}

/** Category/item picker shared by the style and character libraries. */
export function PromptLibrary({ entries, setEntries, categories, defaults, placeholder }: {
  entries: DatasetEntry[]
  setEntries: Dispatch<SetStateAction<DatasetEntry[]>>
  categories: readonly DatasetCategory[]
  defaults: () => DatasetEntry[]
  placeholder: string
}) {
  const [custom, setCustom] = useState('')

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

  return <>
    <fieldset className="dataset-categories">
      <legend>按分类选择</legend>
      {[...categories, CUSTOM].map(category => {
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
      <input type="text" value={custom} maxLength={MAX_DATASET_PROMPT_LENGTH} spellCheck={false} placeholder={placeholder}
        aria-label="自定义提示词" onChange={event => setCustom(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); addCustom() } }} />
      <button className="secondary" type="button" disabled={!custom.trim()} onClick={addCustom}><Plus size={14} aria-hidden="true" /> 添加</button>
      <button className="text-action" type="button" onClick={() => { if (window.confirm('恢复为内置提示词库？自定义和编辑内容将丢失。')) setEntries(defaults()) }}>
        <RotateCcw size={14} aria-hidden="true" /> 恢复默认</button>
    </div>
  </>
}

type DatasetMode = 'style' | 'character'

export const DatasetRunConfig = observer(({ generation, api, hidden }: { generation: GenerationStore; api: WorkspaceApi; hidden: boolean }) => {
  const [mode, setMode] = useState<DatasetMode>('style')
  const [entries, setEntries] = useState<DatasetEntry[]>(defaultDatasetEntries)
  const [characterEntries, setCharacterEntries] = useState<DatasetEntry[]>(defaultCharacterEntries)
  const character = useCharacterSettings(generation.draft.style_prompt)
  const runs = generation.runs
  const snapshot = runs.kind === 'dataset' ? runs.snapshot : null
  const style = generation.draft.style_prompt
  const active = mode === 'style' ? entries : characterEntries
  const selected = active.filter(entry => entry.selected)
  const gptMode = mode === 'character' && character.settings.mode === 'gpt'
  const sampleText = gptMode ? character.settings.gptSamples : generation.draft.sample_count
  const samples = /^\d+$/.test(sampleText) ? Number(sampleText) : null
  const error = !selected.length ? '' : mode === 'style'
    ? childSafetyError(entries, style) || validationError(entries, [style])
    : validationError(characterEntries, character.styles, character.settings.traits) || character.error(generation.draft.model)
  const locked = generation.operationLocked || generation.activeId !== null || generation.busy || generation.submitUncertain

  function start() {
    if (locked || error || !selected.length) return
    if (mode === 'style') void generation.startDatasetRun(entries)
    else void generation.startDatasetRun(characterEntries, {
      styles: character.styles, character: character.settings, gptModel: character.gpt?.gpt_image_model ?? undefined,
    })
  }

  const frozenCharacter = snapshot?.character && 'references' in snapshot.character ? snapshot.character : null

  return <section id="dataset-run-config" className="style-experiment-config dataset-run-config" aria-labelledby="dataset-run-config-title" hidden={hidden}
    onKeyDown={event => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
    <h3 id="dataset-run-config-title"><Layers size={15} aria-hidden="true" /> 训练集批跑</h3>
    {!snapshot && <div className="history-mode dataset-mode" role="group" aria-label="训练集类型">
      <button type="button" className={mode === 'style' ? 'active' : ''} aria-pressed={mode === 'style'} onClick={() => setMode('style')}><Layers size={14} aria-hidden="true" /> 画风训练集</button>
      <button type="button" className={mode === 'character' ? 'active' : ''} aria-pressed={mode === 'character'} onClick={() => setMode('character')}><UserRound size={14} aria-hidden="true" /> 角色训练集</button>
    </div>}
    {mode === 'style'
      ? <p className="prompt-hint">用当前「画风」固定风格，逐条运行下面的内容提示词，生成用于训练画风 LoRA 的图片。提示词只描述内容，不含画风与质量词；导出时作为 caption。默认全选：女性 70 条、成年男性 10 条、年幼男孩 14 条、无人物 15 条；人物条目都写明发色和带颜色的服装，让成图与 caption 对应。「男孩（年幼）」条目不能与身体描写类画风同时使用。</p>
      : <p className="prompt-hint">用参考图和固定的角色特征，逐条运行景别、表情、姿势、场景等内容提示词，生成用于训练角色 LoRA 的图片。导出的 caption 只含内容提示词，不含画风和角色特征。</p>}
    <p className="prompt-hint">公共分区和人物卡片不参与批跑；负面提示词、模型、尺寸、步数、CFG、采样器和每条张数取自当前生成设置。</p>
    {snapshot ? <div className="experiment-note" role="status">
      <p>这里展示本次训练集批跑固定的配置与 {snapshot.items?.length ?? 0} 条提示词。编辑草稿不会改变服务器批跑。</p>
      <p>画风：{snapshot.styles?.length ? snapshot.styles.join(' ｜ ') : snapshot.parameters.style_prompt}</p>
      {frozenCharacter && <p>{characterSnapshotSummary(frozenCharacter)}</p>}
    </div> : mode === 'style' ? <>
      <div className="dataset-style-preview"><span>将应用的画风</span>
        <p>{style.trim() ? style : '（未填写画风）'}</p></div>
      <PromptLibrary entries={entries} setEntries={setEntries} categories={DATASET_CATEGORIES} defaults={defaultDatasetEntries}
        placeholder="添加自定义内容提示词，例如 1girl, solo, sitting, library" />
    </> : <>
      <CharacterRunSettings api={api} state={character} model={generation.draft.model} draftStyle={style} />
      <PromptLibrary entries={characterEntries} setEntries={setCharacterEntries} categories={CHARACTER_CATEGORIES} defaults={defaultCharacterEntries}
        placeholder="添加自定义内容提示词（不写性别、人数和外貌），例如 sitting, library, reading" />
    </>}
    {!snapshot && error && <p className="alert" role="alert">{error}</p>}
    {!snapshot && <div className="experiment-preview" aria-live="polite" aria-atomic="true">
      <p><strong>{selected.length} 条</strong>{samples !== null && samples >= 1 && samples <= 8 && <> × 每条 {samples} 张 = <strong>{selected.length * samples} 张图像</strong></>}
        {selected.length > MAX_DATASET_ITEMS && `（上限 ${MAX_DATASET_ITEMS} 条）`}</p>
      <p className="prompt-hint">{mode === 'style'
        ? '每条提示词是一次付费生成。画风 LoRA 一般 30–150 张精选图即可。'
        : '每条提示词是一次付费生成，Vibe Transfer / 图生图可能额外消耗 Anlas。角色 LoRA 一般 15–40 张一致的精选图即可，跑完请人工筛掉不像的图。'}</p>
    </div>}
    <p className="prompt-hint">每条使用不同种子：生成设置中的种子作为基础种子（留空则服务器随机一次），第 N 条使用基础种子 + N − 1，便于复现。</p>
    <p className="prompt-hint">批跑在服务器依次执行，单条失败后继续下一条，不会自动重试。刷新、关闭页面或退出登录不会停止；只有“停止实验”会阻止后续条目。与画风实验共用“同时只能运行一个”的限制。</p>
    <p className="prompt-hint">图片私有保存 7 天，请在过期前从历史记录的「实验与训练集」中导出训练集。</p>
    {!snapshot && generation.error && !generation.submitUncertain && <p className="alert" role="alert">{generation.error}</p>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={locked || Boolean(error) || !selected.length || selected.length > MAX_DATASET_ITEMS} onClick={start}>
        <Layers size={15} aria-hidden="true" /> 开始批跑
      </button>
    </div>
  </section>
})

export type DatasetExportSource =
  | { kind: 'experiment'; id: string }
  | { kind: 'experiments'; ids: readonly string[] }
  | { kind: 'selection'; ids: readonly string[] }

/** Reads every group of each chosen training set in order (metadata only). */
async function sourceJobs(api: WorkspaceApi, source: DatasetExportSource, signal: AbortSignal): Promise<GenerationView[]> {
  if (source.kind === 'selection') return selectedJobs(api, source.ids, signal)
  const ids = source.kind === 'experiment' ? [source.id] : source.ids
  const jobs: GenerationView[] = []
  for (const id of ids) jobs.push(...await experimentJobs(api, id, signal))
  return jobs
}

export function DatasetExportPanel({ api, source, onClose }: { api: WorkspaceApi; source: DatasetExportSource; onClose: () => void }) {
  const [trigger, setTrigger] = useState('')
  const [prefix, setPrefix] = useState('')
  // Experiment exports load their groups first so the user can drop off-model items.
  const [jobs, setJobs] = useState<GenerationView[] | null>(null)
  const [excluded, setExcluded] = useState<ReadonlySet<string>>(new Set())
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<DatasetExportProgress | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function loadGroups() {
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setRunning(true)
    setError('')
    try {
      if (source.kind !== 'experiment') return
      const loaded = await experimentJobs(api, source.id, current.signal)
      if (controller.current === current) setJobs(loaded)
    } catch (exception) {
      if (!current.signal.aborted) setError(exception instanceof ApiFailure ? errorText(exception) : '读取记录失败，请重试。')
    } finally {
      if (controller.current === current) {
        controller.current = null
        setRunning(false)
      }
    }
  }

  async function run() {
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setRunning(true)
    setError('')
    setMessage('')
    setProgress(null)
    try {
      // Always re-read: groups may have finished or been reviewed since the checklist loaded.
      const all = await sourceJobs(api, source, current.signal)
      const chosen = all.filter(job => !excluded.has(job.id))
      const result = await buildDatasetZip(api, chosen, trigger, prefix, current.signal, setProgress)
      if (current.signal.aborted) return
      const discardedText = result.discarded ? `，已弃置 ${result.discarded} 张未导出` : ''
      if (!result.blob) setError(`没有可导出的图片（跳过 ${result.skipped} 张：失败、已过期或不可用${discardedText}）。`)
      else {
        downloadZip(result.blob, `lora-dataset-${new Date().toISOString().slice(0, 10)}.zip`)
        setMessage(`已导出 ${result.written} 张图片和对应 caption${result.skipped ? `，跳过 ${result.skipped} 张（失败、已过期或不可用）` : ''}${discardedText}。`)
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
    <label className="field"><span>质量词前缀（可选，加在触发词之后、内容标签之前；生成时也写同样的词）</span>
      <input type="text" value={prefix} maxLength={300} spellCheck={false} disabled={running} placeholder="例如 masterpiece, high score, great score, absurdres"
        onChange={event => setPrefix(event.target.value)} /></label>
    <div className="experiment-config-actions">
      <button className="text-action" type="button" disabled={running} onClick={() => setPrefix(ANIMAGINE_QUALITY_PREFIX)}>Animagine XL 4.0 预设</button>
      {prefix && <button className="text-action" type="button" disabled={running} onClick={() => setPrefix('')}>清空前缀</button>}
    </div>
    <p className="prompt-hint">caption 示例：{[trigger.trim(), prefix.trim(), '1girl, solo, portrait, smile…'].filter(Boolean).join(', ')}。只放质量词：皮肤光泽、眼睛细节等希望成为画风的一部分的质感，不要写进 caption。</p>
    <p className="prompt-hint">zip 内为 0001.png + 0001.txt 成对文件。图片去除元数据与隐写信息；caption 只含内容提示词，不含画风和角色特征。已弃置的图片不会导出。导出只读取已保存图片，不会生成。</p>
    {source.kind === 'experiment' && (jobs === null
      ? <button className="text-action" type="button" disabled={running} onClick={() => void loadGroups()}>筛选条目（可选：取消不像角色或不满意的条目）</button>
      : <details className="dataset-category" open><summary><strong>导出条目</strong><span>{jobs.length - excluded.size} / {jobs.length}</span>
          <span className="prompt-hint">可先在「浏览图片」中查看第 N 条，再在这里取消</span></summary>
        <ul className="dataset-items">{jobs.map(job => {
          const context = job.parameters.experiment
          return <li key={job.id} className={excluded.has(job.id) ? 'muted' : ''}>
            <input type="checkbox" checked={!excluded.has(job.id)} disabled={running} aria-label={`导出第 ${context?.ordinal ?? '?'} 条`}
              onChange={event => setExcluded(current => {
                const next = new Set(current)
                if (event.target.checked) next.delete(job.id)
                else next.add(job.id)
                return next
              })} />
            <span>第 {context?.ordinal ?? '?'} 条 · {job.status === 'succeeded' ? `${job.image_urls.length} 张` : '无可用图片'} · {context?.item?.prompt ?? ''}</span>
            <span />
          </li>
        })}</ul></details>)}
    {source.kind === 'experiments' && <p className="prompt-hint">将把所选 {source.ids.length} 个训练集合并导出到一个 zip，编号连续。</p>}
    {progress && <p role="status" aria-live="polite">已处理 {progress.processedJobs} / {progress.totalJobs} 条记录 · 已写入 {progress.written} 张 · 跳过 {progress.skipped} 张 · 已弃置 {progress.discarded} 张</p>}
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
