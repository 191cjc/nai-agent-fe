import { useEffect, useState } from 'react'
import { observer } from 'mobx-react-lite'
import { FlaskConical, RefreshCw, Square } from 'lucide-react'
import { ApiFailure, errorText } from './api'
import { parsePromptTags } from './prompt-weights'
import { createStyleExperimentPlan, type StyleExperimentPlan, type StyleExperimentRange } from './style-experiment'
import { supportsNativeCharacters, type GenerationStore } from './store'
import { PromptSummary } from './PromptSummary'
import type { SavedResultsStore } from './saved-results'

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
  const sourceChanged = configuration.source !== source
  const liveRanges = sourceChanged ? [] : configuration.ranges
  const snapshot = generation.runs.snapshot
  const frozen = snapshot !== null
  const displayed = snapshot ? {
    source: snapshot.parameters.style_prompt,
    ranges: snapshot.ranges.map(range => ({ tagIndex: range.tag_index, min: range.min, max: range.max, step: range.step })),
    sampleCount: String(snapshot.parameters.sample_count),
  } : { source, ranges: liveRanges, sampleCount: generation.draft.sample_count }
  const tags = parsePromptTags(displayed.source)
  const { plan, error } = planPreview(displayed.source, displayed.ranges)
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
    if (locked || !plan || !samples || !supportedModel || configuration.source !== source) return
    const ranges = liveRanges.map(range => ({ ...range }))
    void generation.startStyleExperiment(source, ranges)
  }

  return <section id="style-experiment-config" className="style-experiment-config" aria-labelledby="style-experiment-config-title" hidden={hidden}
    onKeyDown={event => { if (event.key === 'Enter' && event.target instanceof HTMLInputElement) event.preventDefault() }}>
    <h3 id="style-experiment-config-title"><FlaskConical size={15} aria-hidden="true" /> 画风实验</h3>
    <p className="prompt-hint">选择要模糊测试的画风词条，为每个词条设置下限、上限和步长，依次尝试所有权重组合。</p>
    {frozen && <p className="experiment-note" role="status">这里展示本次实验固定的画风和范围。编辑草稿不会改变服务器实验。</p>}
    {!frozen && notice && <p className="experiment-note" role="status">{notice}</p>}
    <fieldset className="experiment-tag-options" disabled={frozen}>
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
    <p className="prompt-hint">实验在服务器依次执行，单组失败后继续下一组。刷新、关闭页面、断线或退出登录都不会停止；重新进入会接回进度。只在点击“停止实验”后停止后续组。</p>
    <p className="prompt-hint">新图片私有保存 7 天，参数和权重保留更久；从进度区或历史记录的“画风实验”打开对比。</p>
    {!frozen && !supportedModel && <p className="experiment-note">画风实验需要生成设置列表中的 V4 / V4.5 / V5 模型。</p>}
    {!frozen && generation.error && !generation.submitUncertain && <p className="alert" role="alert">{generation.error}</p>}
    <div className="experiment-config-actions">
      <button className="primary" type="button" disabled={locked || !plan || samples === null || !supportedModel} onClick={start}>
        <FlaskConical size={15} aria-hidden="true" /> 开始批量测试
      </button>
    </div>
  </section>
})

function experimentStatus(status: string): string {
  return { running: '服务器运行中', stopping: '正在停止', stopped: '已停止', completed: '已完成' }[status] ?? status
}

export const StyleExperimentProgress = observer(({ generation, saved }: { generation: GenerationStore; saved: SavedResultsStore }) => {
  const runs = generation.runs
  const run = runs.run
  if (!run && runs.initialized && !runs.pendingId && !runs.error && !runs.creating) return null
  const stateLabel = run ? experimentStatus(run.status) : runs.creating ? '正在创建'
    : runs.pendingId ? '提交待核对' : runs.checking ? '正在检查服务器' : '等待连接'
  return <div className="experiment-progress" aria-label="画风实验进度">
    <div className="experiment-progress-line" role="status" aria-live="polite" aria-atomic="true">
      <strong>画风实验 · {stateLabel}</strong>
      {run && <>
        <span>已处理 {run.processed_count} / {run.total} 组</span>
        <span>成功 {run.succeeded_count} · 失败 {run.failed_count}</span>
        {run.current_ordinal !== null && <span>当前第 {run.current_ordinal} 组</span>}
        {runs.running && !runs.connected && <span>进度连接中断，后台可能仍在运行</span>}
      </>}
      {runs.pendingId && <span>实验编号 {runs.pendingId}</span>}
    </div>
    <div className="server-run-actions">
      <button className="secondary" type="button" disabled={runs.creating || runs.checking || runs.stopping}
        onClick={() => void runs.refresh()}><RefreshCw size={14} aria-hidden="true" />{runs.checking ? '正在连接...' : runs.connected ? '刷新进度' : '重新连接'}</button>
      {run && <button className="secondary" type="button" onClick={() => void saved.openExperiment(run.id)}>
        <FlaskConical size={14} aria-hidden="true" /> 查看已保存结果
      </button>}
      {(runs.running || runs.pendingId) && <button className="secondary" type="button"
        disabled={runs.creating || runs.stopping || run?.status === 'stopping'} onClick={() => void runs.stop()}>
        <Square size={13} aria-hidden="true" />{runs.stopping ? '正在请求停止...' : run?.status === 'stopping' ? '等待当前组结束' : '停止实验'}
      </button>}
    </div>
    {runs.error && <p className="alert" role="alert">{runs.error}</p>}
    {runs.stopError && <p className="alert" role="alert">{runs.stopError}</p>}
    {runs.pendingId && runs.missing && <button className="text-action" type="button" disabled={runs.creating || runs.checking || runs.stopping}
      onClick={() => {
        if (window.confirm('请先核对历史和已保存实验。解除锁后将再次检查服务器是否有活动实验，不会重新提交原实验。确认已核对？')) void runs.acknowledgeMissing()
      }}>已核对历史，解除未知提交锁</button>}
    {run?.error_code && <p className="experiment-note">最近一组诊断：{errorText(new ApiFailure(0, run.error_code, '本组处理失败。'))}
      {run.status === 'running' && ' 服务器会继续处理后续组，不会重试这一组。'}</p>}
    {run && <details className="result-parameters server-run-snapshot"><summary>实验信息与固定配置</summary>
      <p>每组 {run.sample_count} 张 · 计划 {(BigInt(run.total) * BigInt(run.sample_count)).toString()} 张 · 统一请求种子 {run.seed}</p>
      <PromptSummary parameters={run.parameters} />
      {run.parameters.negative_prompt && <p>负向：{run.parameters.negative_prompt}</p>}
      <ul>{run.ranges.map(range => <li key={range.tag_index}>词条 {range.tag_index + 1} · {range.min} → {range.max} · 步长 {range.step}</li>)}</ul>
      <p>{run.parameters.model} · {run.parameters.width}×{run.parameters.height} · {run.parameters.sampler}</p>
      <p>{run.parameters.steps} 步 · CFG {run.parameters.cfg_scale} · 每组 {run.sample_count} 张 · {run.parameters.quality ? '高质量' : '标准质量'}</p>
      <p>原始请求种子 {run.parameters.seed ?? '随机'} · 统一实际种子 {run.seed}</p>
      <p>实验编号 {run.id} · {new Date(run.created_at * 1000).toLocaleString()}</p>
      <p>服务器执行实验；离开页面或退出登录仅断开查看。单组失败会继续后续组，只有“停止实验”会阻止新的组。</p>
    </details>}
  </div>
})
