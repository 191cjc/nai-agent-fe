import { useEffect, useState } from 'react'
import { observer } from 'mobx-react-lite'
import { FlaskConical, RefreshCw, Square, X } from 'lucide-react'
import { ApiFailure, errorText, type ExperimentRunState } from './api'
import { datasetItemText } from './dataset-run'
import { parsePromptTags } from './prompt-weights'
import { createStyleExperimentPlan, type StyleExperimentPlan, type StyleExperimentRange } from './style-experiment'
import { supportsNativeCharacters, type GenerationStore } from './store'
import { PromptSummary } from './PromptSummary'
import { characterSnapshotSummary } from './character-summary'
import type { SavedResultsStore } from './saved-results'
import type { StyleRunStore } from './style-run-store'
import { sharedPrompt } from './prompt-sections'

interface Configuration {
  source: string
  ranges: StyleExperimentRange[]
  notice: string
}

const SOURCE_CHANGED = '画风已修改，已清除所选词条，请重新选择。'

function sampleCount(value: string): bigint | null {
  if (!/^\d+$/.test(value)) return null
  const count = BigInt(value)
  return count >= 1n && count <= 8n ? count : null
}

function planPreview(source: string, ranges: StyleExperimentRange[], comments: boolean): { plan: StyleExperimentPlan | null; error: string } {
  if (!ranges.length) return { plan: null, error: '' }
  try {
    return { plan: createStyleExperimentPlan(source, ranges, comments), error: '' }
  } catch (error) {
    return { plan: null, error: error instanceof Error ? error.message : '实验范围无效。' }
  }
}

export const StyleExperimentConfig = observer(({ generation, hidden }: { generation: GenerationStore; hidden: boolean }) => {
  const source = generation.draft.style_prompt
  const [configuration, setConfiguration] = useState<Configuration>({ source, ranges: [], notice: '' })
  const sourceChanged = configuration.source !== source
  const liveRanges = sourceChanged ? [] : configuration.ranges
  // A dataset run has no weight ranges; its own panel shows the frozen definition.
  const snapshot = generation.runs.kind === 'style' ? generation.runs.snapshot : null
  const frozen = snapshot !== null
  const displayed = snapshot ? {
    source: snapshot.parameters.style_prompt,
    ranges: snapshot.ranges.map(range => ({ tagIndex: range.tag_index, min: range.min, max: range.max, step: range.step })),
    sampleCount: String(snapshot.parameters.sample_count),
  } : { source, ranges: liveRanges, sampleCount: generation.draft.sample_count }
  const comments = snapshot ? snapshot.parameters.prompt_comments === true : true
  const tags = parsePromptTags(displayed.source, comments)
  const { plan, error: planError } = planPreview(displayed.source, displayed.ranges, comments)
  const error = planError || (!frozen && plan?.canBeEmpty && !sharedPrompt(generation.draft.shared_sections).trim()
    ? '权重为 0 时可能移除全部画风词条，请填写公共提示词，或调整范围以保留至少一个画风词条。' : '')
  const samples = sampleCount(displayed.sampleCount)
  const supportedModel = supportsNativeCharacters(snapshot?.parameters.model ?? generation.draft.model)
  const notice = sourceChanged && configuration.ranges.length ? SOURCE_CHANGED : configuration.notice
  const locked = generation.operationLocked || generation.activeId !== null || generation.busy || generation.submitUncertain

  useEffect(() => {
    setConfiguration(current => current.source === source ? current : {
      source, ranges: [], notice: current.ranges.length ? SOURCE_CHANGED : current.notice,
    })
  }, [source])

  function select(tagIndex: number, selected: boolean) {
    setConfiguration(current => {
      const ranges = current.source === source ? current.ranges : []
      return {
        source, notice: '', ranges: selected
          ? [...ranges, { tagIndex, min: '0.5', max: '1.5', step: '0.1' }]
          : ranges.filter(range => range.tagIndex !== tagIndex),
      }
    })
  }

  function changeRange(tagIndex: number, name: 'min' | 'max' | 'step', value: string) {
    setConfiguration(current => current.source !== source ? { source, ranges: [], notice: SOURCE_CHANGED } : {
      ...current, notice: '', ranges: current.ranges.map(range => range.tagIndex === tagIndex ? { ...range, [name]: value } : range),
    })
  }

  function start() {
    if (locked || error || !plan || !samples || !supportedModel || configuration.source !== source) return
    const ranges = liveRanges.map(range => ({ ...range }))
    void generation.startStyleExperiment(source, ranges)
  }

  return <section id="style-experiment-config" className="style-experiment-config" aria-labelledby="style-experiment-config-title" hidden={hidden}
    onKeyDown={event => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
    <h3 id="style-experiment-config-title"><FlaskConical size={15} aria-hidden="true" /> 画风实验</h3>
    <p className="prompt-hint">选择要模糊测试的画风词条，为每个词条设置下限、上限和步长，依次尝试所有权重组合。</p>
    <p className="prompt-hint">新实验中，权重为 0 时移除该词条。已隐藏的词条不参与实验。</p>
    {frozen && <p className="experiment-note" role="status">这里展示本次实验固定的画风和范围。编辑草稿不会改变服务器实验。</p>}
    {!frozen && notice && <p className="experiment-note" role="status">{notice}</p>}
    <fieldset className="experiment-tag-options" disabled={frozen}>
      <legend>模糊画风词条</legend>
      {tags.length ? tags.map((tag, tagIndex) => <label className={`experiment-tag-option${tag.weight === null ? ' original' : ''}${tag.hidden ? ' muted' : ''}`} key={tagIndex}>
        <input type="checkbox" checked={displayed.ranges.some(range => range.tagIndex === tagIndex)} disabled={tag.hidden || tag.manualOnly || tag.weight === null}
          onChange={event => select(tagIndex, event.target.checked)} />
        <span className="experiment-occurrence">{tagIndex + 1}.</span>
        <span className="experiment-tag-label">{tag.text}</span>
        <span className="experiment-current-weight" title={tag.hidden ? '已隐藏 · 不参与实验' : tag.weight === null ? '原文 · 仅手动编辑' : `当前 ${tag.weight}`}>
          {tag.hidden ? '已隐藏' : tag.weight === null ? '原文 · 仅手动编辑' : `当前 ${tag.weight}`}</span>
      </label>) : <p className="prompt-hint">先在画风中填写词条，再选择需要测试的词条。</p>}
    </fieldset>
    <div className="experiment-ranges">{[...displayed.ranges].sort((left, right) => left.tagIndex - right.tagIndex).map(range => {
      const tag = tags[range.tagIndex]
      return <fieldset className="experiment-range" disabled={frozen} key={range.tagIndex}>
        <legend>{range.tagIndex + 1}. {tag?.text}</legend>
        <div className="experiment-range-fields">{([['min', '下限'], ['max', '上限'], ['step', '步长']] as const).map(([name, label]) =>
          <label className="field" key={name} htmlFor={`experiment-${range.tagIndex}-${name}`}><span>{label}</span>
            <input id={`experiment-${range.tagIndex}-${name}`} type="text" inputMode="decimal" autoComplete="off" spellCheck={false}
              value={range[name]} aria-label={`词条 ${range.tagIndex + 1}：${tag?.text}，${label}`}
              onChange={event => changeRange(range.tagIndex, name, event.target.value)} /></label>)}</div>
      </fieldset>
    })}</div>
    {error && <p className="alert" role="alert">{error}</p>}
    {plan && <div className="experiment-preview" aria-live="polite" aria-atomic="true">
      <ul>{plan.dimensions.map(dimension => <li key={dimension.tagIndex}>
        <span>{dimension.tagIndex + 1}. {dimension.label}</span>
        <span>{dimension.min} → {dimension.max} · 步长 {dimension.step} · {dimension.count.toString()} 个值</span>
      </li>)}</ul>
      <p><strong>{plan.total.toString()} 组</strong>{samples !== null && <> × 每组 {samples.toString()} 张 = <strong>{(plan.total * samples).toString()} 张图像</strong></>}</p>
      {samples === null && <p className="experiment-note">请在生成设置中将每组张数设为 1–8。</p>}
      <p className="prompt-hint">从下限递增，未恰好落在步长上的上限不追加；按词条顺序组合，最后一个词条变化最快。</p>
    </div>}
    <p className="prompt-hint">固定种子用于所有组；留空时服务器在创建实验时随机一次，即使首组失败也沿用同一种子。</p>
    <p className="prompt-hint">实验在服务器依次执行，单组失败后继续下一组。已有实验或训练集在运行时，新实验加入队列，按顺序开始。刷新、关闭页面、断线或退出登录都不会停止；重新进入会接回进度。只在点击“停止”后停止后续组。</p>
    <p className="prompt-hint">新图片私有保存 7 天，参数和权重保留更久；从进度区或历史记录的“画风实验”打开对比。</p>
    {!frozen && !supportedModel && <p className="experiment-note">画风实验需要生成设置列表中的 V4 / V4.5 / V5 模型。</p>}
    {!frozen && generation.error && !generation.submitUncertain && <p className="alert" role="alert">{generation.error}</p>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={locked || Boolean(error) || !plan || samples === null || !supportedModel} onClick={start}>
        <FlaskConical size={15} aria-hidden="true" /> {generation.runs.running ? '加入队列' : '开始批量测试'}
      </button>
    </div>
  </section>
})

function runStatus(run: ExperimentRunState): string {
  if (run.status === 'running') return run.queue_position ? `排队中 · 前面还有 ${run.queue_position} 个` : '生成中'
  return { stopping: '正在停止', stopped: '已停止', completed: '已完成' }[run.status] ?? run.status
}

const LANES = { novelai: 'NovelAI', gpt: 'GPT' } as const

/** Items a GPT run generates at once; lowering it lets in-flight items finish first. */
function ParallelismControl({ runs, run }: { runs: StyleRunStore; run: ExperimentRunState }) {
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const current = run.parallelism ?? null
  async function apply() {
    const value = Number(draft.trim())
    if (!Number.isInteger(value) || value < 1 || value > 16) { setMessage('请输入 1–16 的整数。'); return }
    setSaving(true)
    setMessage('')
    const failure = await runs.setParallelism(run.id, value)
    setSaving(false)
    setMessage(failure)
    if (!failure) setDraft('')
  }
  return <form className="run-parallelism" onSubmit={event => { event.preventDefault(); void apply() }}>
    <span>同时生成：{current ?? '服务器上限'} 条</span>
    <input type="text" inputMode="numeric" aria-label="新的同时生成条数" placeholder="1–16" value={draft} disabled={saving}
      onChange={event => setDraft(event.target.value)} />
    <button className="secondary" type="submit" disabled={saving || !draft.trim()}>{saving ? '保存中...' : '调整'}</button>
    {message && <span className="alert" role="alert">{message}</span>}
  </form>
}

const RunRow = observer(({ runs, run, saved }: { runs: StyleRunStore; run: ExperimentRunState; saved: SavedResultsStore }) => {
  const dataset = run.kind === 'dataset'
  const character = dataset && !!run.character
  const unit = dataset ? '条' : '组'
  const fallback = dataset ? (character ? '角色训练集' : '画风训练集') : '画风实验'
  const unfinished = run.status === 'running' || run.status === 'stopping'
  const queued = run.status === 'running' && !!run.queue_position
  const stopping = runs.isStopping(run.id)
  return <li className={`run-queue-item${queued ? ' queued' : ''}`}>
    <div className="experiment-progress-line" role="status" aria-live="polite" aria-atomic="true">
      <span className={`dataset-type-badge ${character ? 'character' : 'style'}`}>{dataset ? (character ? '角色' : '画风') : '实验'}</span>
      <strong>{run.name || fallback} · {runStatus(run)}</strong>
      <span className="run-lane">{LANES[run.lane ?? 'novelai']}</span>
      <span>已处理 {run.processed_count} / {run.total} {unit}</span>
      <span>成功 {run.succeeded_count} · 失败 {run.failed_count}</span>
      {(run.in_flight_count ?? 0) > 1
        ? <span>并发生成 {run.in_flight_count} {unit}（最早第 {run.current_ordinal} {unit}）</span>
        : run.current_ordinal !== null && <span>当前第 {run.current_ordinal} {unit}</span>}
    </div>
    <div className="server-run-actions">
      {!queued && <button className="secondary" type="button" onClick={() => void saved.openExperiment(run.id)}>
        <FlaskConical size={14} aria-hidden="true" /> 查看已保存结果
      </button>}
      {unfinished ? <button className="secondary" type="button" disabled={stopping || run.status === 'stopping'} onClick={() => {
        if (queued || window.confirm(`停止「${run.name || fallback}」？进行中的${unit}会完成，后续${unit}不再生成。`)) void runs.stop(run.id)
      }}>
        <Square size={13} aria-hidden="true" />{stopping ? '正在请求停止...' : run.status === 'stopping' ? `等待当前${unit}结束` : queued ? '取消排队' : '停止'}
      </button> : <button className="icon-button" type="button" title="从列表移除" aria-label={`从列表移除 ${run.name || fallback}`}
        onClick={() => runs.dismissFinished(run.id)}><X size={14} aria-hidden="true" /></button>}
    </div>
    {unfinished && run.lane === 'gpt' && <ParallelismControl runs={runs} run={run} />}
    {run.error_code && <p className="experiment-note">最近一{unit}诊断：{errorText(new ApiFailure(0, run.error_code, `本${unit}处理失败。`))}
      {run.status === 'running' && ` 服务器会继续处理后续${unit}，不会重试这一${unit}。`}</p>}
    <details className="result-parameters server-run-snapshot"><summary>{dataset ? '批跑信息与固定配置' : '实验信息与固定配置'}</summary>
      <p>每{unit} {run.sample_count} 张 · 计划 {(BigInt(run.total) * BigInt(run.sample_count)).toString()} 张 · {dataset ? `基础种子 ${run.seed}，第 N 条使用基础种子 + N − 1` : `统一请求种子 ${run.seed}`}</p>
      <PromptSummary parameters={run.parameters} />
      {run.parameters.negative_prompt && <p>负向：{run.parameters.negative_prompt}</p>}
      {run.character && 'references' in run.character && <p>{characterSnapshotSummary(run.character)}</p>}
      {run.styles && run.styles.length > 1 && <p>画风池：{run.styles.join(' ｜ ')}</p>}
      {dataset && <details><summary>{run.items?.length ?? 0} 条提示词</summary>
        <ol className="dataset-run-items">{run.items?.map(item => <li key={item.id}>{datasetItemText(item)}</li>)}</ol></details>}
      <ul>{run.ranges.map(range => <li key={range.tag_index}>词条 {range.tag_index + 1} · {range.min} → {range.max} · 步长 {range.step}</li>)}</ul>
      <p>{run.parameters.model} · {run.parameters.width}×{run.parameters.height} · {run.parameters.sampler}</p>
      <p>{run.parameters.steps} 步 · CFG {run.parameters.cfg_scale} · 每{unit} {run.sample_count} 张 · {run.parameters.quality ? '高质量' : '标准质量'}</p>
      <p>原始请求种子 {run.parameters.seed ?? '随机'} · {dataset ? '基础' : '统一'}实际种子 {run.seed}</p>
      <p>实验编号 {run.id} · {new Date(run.created_at * 1000).toLocaleString()}</p>
    </details>
  </li>
})

export const StyleExperimentProgress = observer(({ generation, saved }: { generation: GenerationStore; saved: SavedResultsStore }) => {
  const runs = generation.runs
  const visible = runs.runs.length > 0 || runs.finished.length > 0 || runs.pendingId !== null || runs.creating
    || !!runs.error || !!runs.createError || !!runs.stopError || !runs.initialized
  if (!visible || (!runs.initialized && runs.checking && !runs.error)) return null
  const pendingLabel = runs.creating ? '正在加入队列' : runs.pendingId ? '提交待核对' : ''
  return <div className="experiment-progress run-queue" aria-label="实验与训练集队列">
    <div className="experiment-progress-line">
      <strong>实验与训练集队列</strong>
      <span>{runs.runs.length ? `${runs.runs.length} 个未完成 · NovelAI 与 GPT 各自按顺序执行` : '没有未完成的任务'}</span>
      {runs.running && !runs.connected && <span>进度连接中断，后台可能仍在运行</span>}
      {pendingLabel && <span>{pendingLabel}{runs.pendingId && ` · 编号 ${runs.pendingId}`}</span>}
    </div>
    <div className="server-run-actions">
      <button className="secondary" type="button" disabled={runs.creating || runs.checking}
        onClick={() => void runs.refresh()}><RefreshCw size={14} aria-hidden="true" />{runs.checking ? '正在连接...' : runs.connected ? '刷新进度' : '重新连接'}</button>
      {runs.finished.length > 0 && <button className="secondary" type="button" onClick={() => runs.dismissFinished()}>清除已结束</button>}
    </div>
    {runs.error && <p className="alert" role="alert">{runs.error}</p>}
    {runs.createError && <p className="alert" role="alert">{runs.createError}</p>}
    {runs.stopError && <p className="alert" role="alert">{runs.stopError}</p>}
    {runs.pendingId && runs.missing && <button className="text-action" type="button" disabled={runs.creating || runs.checking}
      onClick={() => {
        if (window.confirm('请先核对历史和已保存实验。解除锁后将重新读取服务器队列，不会重新提交原实验。确认已核对？')) void runs.acknowledgeMissing()
      }}>已核对历史，解除未知提交锁</button>}
    {(runs.runs.length > 0 || runs.finished.length > 0) && <ol className="run-queue-list">
      {runs.runs.map(run => <RunRow key={run.id} runs={runs} run={run} saved={saved} />)}
      {runs.finished.map(run => <RunRow key={run.id} runs={runs} run={run} saved={saved} />)}
    </ol>}
    <p className="experiment-note">服务器执行队列；离开页面或退出登录仅断开查看。单{'条/组'}失败会继续后续内容，只有“停止”会阻止后续生成。</p>
  </div>
})
