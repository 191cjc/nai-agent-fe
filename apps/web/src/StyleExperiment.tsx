import { useEffect, useState } from 'react'
import { observer } from 'mobx-react-lite'
import { ArrowDownToLine, ArrowLeft, ArrowRight, FlaskConical, Square, Trash2 } from 'lucide-react'
import { ApiFailure, errorText } from './api'
import { parsePromptTags } from './prompt-weights'
import { createStyleExperimentPlan, type StyleExperimentPlan, type StyleExperimentRange } from './style-experiment'
import { supportsNativeCharacters, type GenerationStore } from './store'

interface Configuration {
  source: string
  ranges: StyleExperimentRange[]
  notice: string
}

interface RunConfiguration {
  source: string
  ranges: StyleExperimentRange[]
  sampleCount: string
}

const SOURCE_CHANGED = '画风已修改，已清除所选词条，请重新选择。'
const RESULTS_PER_PAGE = 6

function sampleCount(value: string): bigint | null {
  if (!/^\d+$/.test(value)) return null
  const count = BigInt(value)
  return count >= 1n && count <= 8n ? count : null
}

function planPreview(source: string, ranges: StyleExperimentRange[]): { plan: StyleExperimentPlan | null; error: string } {
  if (!ranges.length) return { plan: null, error: '' }
  try {
    return { plan: createStyleExperimentPlan(source, ranges), error: '' }
  } catch (error) {
    return { plan: null, error: error instanceof Error ? error.message : '实验范围无效。' }
  }
}

export const StyleExperimentConfig = observer(({ generation, hidden }: { generation: GenerationStore; hidden: boolean }) => {
  const source = generation.draft.style_prompt
  const [configuration, setConfiguration] = useState<Configuration>({ source, ranges: [], notice: '' })
  const [runConfiguration, setRunConfiguration] = useState<RunConfiguration | null>(null)
  const sourceChanged = configuration.source !== source
  const liveRanges = sourceChanged ? [] : configuration.ranges
  const running = generation.experimentRunning
  const displayed = running && runConfiguration
    ? runConfiguration : { source, ranges: liveRanges, sampleCount: generation.draft.sample_count }
  const tags = parsePromptTags(displayed.source)
  const { plan, error } = planPreview(displayed.source, displayed.ranges)
  const samples = sampleCount(displayed.sampleCount)
  const supportedModel = supportsNativeCharacters(generation.draft.model)
  const notice = sourceChanged && configuration.ranges.length ? SOURCE_CHANGED : configuration.notice
  const locked = running || generation.operationLocked || generation.activeId !== null || generation.busy || generation.submitUncertain

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
    if (locked || !plan || !samples || !supportedModel || configuration.source !== source) return
    const ranges = liveRanges.map(range => ({ ...range }))
    setRunConfiguration({ source, ranges, sampleCount: generation.draft.sample_count })
    void generation.startStyleExperiment(source, ranges)
  }

  return <section id="style-experiment-config" className="style-experiment-config" aria-labelledby="style-experiment-config-title" hidden={hidden}
    onKeyDown={event => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
    <h3 id="style-experiment-config-title"><FlaskConical size={15} aria-hidden="true" /> 画风实验</h3>
    <p className="prompt-hint">选择要模糊测试的画风词条，为每个词条设置下限、上限和步长，依次尝试所有权重组合。</p>
    {running && <p className="experiment-note" role="status">正在使用开始时的画风和生成设置。编辑草稿不会改变本次实验。</p>}
    {!running && notice && <p className="experiment-note" role="status">{notice}</p>}
    <fieldset className="experiment-tag-options" disabled={running}>
      <legend>模糊画风词条</legend>
      {tags.length ? tags.map((tag, tagIndex) => <label className={tag.weight === null ? 'experiment-tag-option original' : 'experiment-tag-option'} key={tagIndex}>
        <input type="checkbox" checked={displayed.ranges.some(range => range.tagIndex === tagIndex)} disabled={tag.weight === null}
          onChange={event => select(tagIndex, event.target.checked)} />
        <span className="experiment-occurrence">{tagIndex + 1}.</span>
        <span className="experiment-tag-label">{tag.text}</span>
        <span className="experiment-current-weight" title={tag.weight === null ? '原文 · 仅手动编辑' : `当前 ${tag.weight}`}>
          {tag.weight === null ? '原文 · 仅手动编辑' : `当前 ${tag.weight}`}</span>
      </label>) : <p className="prompt-hint">先在画风中填写词条，再选择需要测试的词条。</p>}
    </fieldset>
    <div className="experiment-ranges">{[...displayed.ranges].sort((left, right) => left.tagIndex - right.tagIndex).map(range => {
      const tag = tags[range.tagIndex]
      return <fieldset className="experiment-range" disabled={running} key={range.tagIndex}>
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
    <p className="prompt-hint">固定种子会用于所有组；种子留空时仅第一组随机，之后沿用第一组的实际种子。</p>
    <p className="prompt-hint">实验和对比图像仅保留在当前页面。刷新、关闭页面或停止会阻止后续组，已提交的组仍可能完成；每组参数保存在历史记录中。</p>
    <p className="prompt-hint">开始新实验会替换上一次的对比结果，请先下载需要保留的图像。</p>
    {!running && !supportedModel && <p className="experiment-note">画风实验需要生成设置列表中的 V4 / V4.5 / V5 模型。</p>}
    {!running && generation.error && !generation.submitUncertain && <p className="alert" role="alert">{generation.error}</p>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={locked || !plan || samples === null || !supportedModel} onClick={start}>
        <FlaskConical size={15} aria-hidden="true" /> 开始批量测试
      </button>
    </div>
  </section>
})

function experimentStatus(status: string): string {
  return { running: '测试中', stopping: '正在停止', stopped: '已停止', completed: '全部完成', failed: '实验已中止' }[status] ?? status
}

function jobStatus(status: string): string {
  return { queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[status] ?? status
}

export const StyleExperimentProgress = observer(({ generation }: { generation: GenerationStore }) => {
  const experiment = generation.experiment
  if (!experiment) return null
  return <div className="experiment-progress" aria-label="画风实验进度">
    <div className="experiment-progress-line" role="status" aria-live="polite" aria-atomic="true">
      <strong>画风实验 · {experimentStatus(experiment.status)}</strong>
      <span>已处理 {experiment.completed.toString()} / {experiment.total.toString()} 组</span>
      <span>每组 {experiment.sampleCount} 张 · 共 {(experiment.total * BigInt(experiment.sampleCount)).toString()} 张</span>
      {generation.experimentRunning && <span>当前第 {experiment.current.toString()} 组</span>}
      <span>{experiment.seed === null ? '种子：等待第一组结果' : `统一请求种子 ${experiment.seed}`}</span>
    </div>
    {generation.experimentRunning && <button className="secondary" type="button" disabled={experiment.status === 'stopping'} onClick={() => generation.stopStyleExperiment()}>
      <Square size={13} aria-hidden="true" /> {experiment.status === 'stopping' ? '等待当前组完成' : '停止后续组'}
    </button>}
    {experiment.error && <p className="alert" role="alert">{experiment.error}</p>}
  </div>
})

export const StyleExperimentResults = observer(({ generation }: { generation: GenerationStore }) => {
  const [page, setPage] = useState(0)
  const experiment = generation.experiment
  useEffect(() => { setPage(0) }, [experiment])
  if (!experiment || !experiment.results.length) return null
  const pageCount = Math.ceil(experiment.results.length / RESULTS_PER_PAGE)
  const currentPage = Math.min(page, pageCount - 1)
  const rows = experiment.results.slice(currentPage * RESULTS_PER_PAGE, (currentPage + 1) * RESULTS_PER_PAGE)
  return <section className="experiment-results" aria-labelledby="experiment-results-title">
    <div className="section-heading">
      <div><span className="eyebrow">画风实验</span><h2 id="experiment-results-title">权重组合对比</h2></div>
      <button className="text-action" type="button" disabled={generation.experimentRunning || generation.operationLocked || generation.activeId !== null || generation.busy}
        onClick={() => generation.clearStyleExperimentResults()}><Trash2 size={14} aria-hidden="true" /> 清除对比结果</button>
    </div>
    <p className="subtle">已保留 {experiment.results.length} 组。图像仅在当前页面内存中可用，请及时下载。</p>
    <div className="experiment-result-list">{rows.map(row => <article className="experiment-result-card" key={row.job.id}>
      <div className="experiment-result-heading"><h3>第 {row.ordinal.toString()} 组</h3>
        <span className={`status status-${row.job.status}`}>{jobStatus(row.job.status)}</span>
        <span>请求种子 {row.job.parameters.seed ?? '随机'}</span>
        {row.job.parameters.seed === null && <span>实际种子 {row.job.effective_seed}</span>}
      </div>
      <ul className="experiment-result-weights" aria-label={`第 ${row.ordinal.toString()} 组权重`}>{row.weights.map(weight =>
        <li key={weight.tagIndex}><span>{weight.tagIndex + 1}. {weight.label}</span><strong>{weight.weight}</strong></li>)}</ul>
      <details className="result-parameters"><summary>本组生成参数</summary>
        <p>画风：{row.job.parameters.style_prompt}</p>
        <p>{row.job.parameters.model} · {row.job.parameters.width}×{row.job.parameters.height} · {row.job.parameters.sampler}</p>
        <p>{row.job.parameters.steps} 步 · CFG {row.job.parameters.cfg_scale} · 每组 {row.job.parameters.sample_count} 张</p>
      </details>
      {row.job.error_code && <p className="alert" role="alert">{errorText(new ApiFailure(0, row.job.error_code, '本组生成失败。'))}</p>}
      {row.imageError && <p className="alert" role="alert">{row.imageError}</p>}
      {row.images.length ? <div className="image-grid">{row.images.map(image => <figure className="image-item" key={image.url}>
        <img src={image.url} loading="lazy" alt={`画风实验第 ${row.ordinal.toString()} 组，图像 ${image.index + 1}`} />
        <figcaption><span>第 {row.ordinal.toString()} 组 · 图像 {image.index + 1}</span>
          <a href={image.url} download={`style-experiment-${row.ordinal.toString()}-${image.filename}`} className="icon-button"
            title={`下载第 ${row.ordinal.toString()} 组图像 ${image.index + 1}`} aria-label={`下载第 ${row.ordinal.toString()} 组图像 ${image.index + 1}`}>
            <ArrowDownToLine size={17} aria-hidden="true" /></a>
        </figcaption>
      </figure>)}</div> : <p className="subtle">本组没有可展示的图像。</p>}
    </article>)}</div>
    <nav className="pager" aria-label="画风实验结果分页">
      <button className="icon-button" type="button" title="上一页实验结果" aria-label="上一页实验结果" disabled={currentPage === 0}
        onClick={() => setPage(currentPage - 1)}><ArrowLeft size={18} aria-hidden="true" /></button>
      <span>第 {currentPage + 1} / {pageCount} 页 · 共 {experiment.results.length} 组</span>
      <button className="icon-button" type="button" title="下一页实验结果" aria-label="下一页实验结果" disabled={currentPage + 1 >= pageCount}
        onClick={() => setPage(currentPage + 1)}><ArrowRight size={18} aria-hidden="true" /></button>
    </nav>
  </section>
})
