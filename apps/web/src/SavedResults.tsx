import { useEffect, useRef } from 'react'
import { observer } from 'mobx-react-lite'
import { ArrowDownToLine, ArrowLeft, ArrowRight, FlaskConical, RefreshCw, X } from 'lucide-react'
import { ApiFailure, errorText } from './api'
import { PromptSummary } from './PromptSummary'
import type { SavedResultsStore } from './saved-results'

export const SavedExperimentList = observer(({ saved, onView }: { saved: SavedResultsStore; onView: () => void }) => {
  return <div className="saved-experiment-list">
    <div className="history-toolbar"><span>已保存的画风实验</span>
      <button type="button" className="icon-button" title="刷新已保存实验" aria-label="刷新已保存实验" disabled={saved.listLoading}
        onClick={() => void saved.loadExperiments()}><RefreshCw size={17} /></button>
    </div>
    <p className="prompt-hint">新图像由服务器私有保存 7 天；参数和权重保留更久。刷新后可在这里重新对比，服务器实验的进度会在工作台接回。</p>
    {!saved.listLoaded && !saved.listLoading && <button className="secondary" type="button" onClick={() => void saved.loadExperiments(0)}>加载已保存实验</button>}
    {saved.listLoading && <p className="subtle" role="status">正在加载实验...</p>}
    {saved.listError && <p className="alert" role="alert">{saved.listError}</p>}
    {saved.listLoaded && !saved.listLoading && !saved.listError && !saved.experiments.length && <p className="subtle">暂无已保存的画风实验</p>}
    <div className="history-list">{saved.experiments.map(experiment => <article className="history-item saved-experiment-item" key={experiment.id}>
      <time dateTime={new Date(experiment.created_at * 1000).toISOString()}>{new Date(experiment.created_at * 1000).toLocaleString()}</time>
      <p>已提交 <strong>{experiment.group_count}</strong> / {experiment.total} 组</p>
      <p className="history-meta">已结束 {experiment.completed_count} 组 · 曾生成 {experiment.image_count} 张（含已过期图像）</p>
      <button className="text-action" type="button" onClick={() => { void saved.openExperiment(experiment.id); onView() }}>
        <FlaskConical size={15} aria-hidden="true" /> 打开对比
      </button>
    </article>)}</div>
    {saved.listLoaded && <div className="pager">
      <button className="icon-button" type="button" title="上一页实验" aria-label="上一页实验" disabled={saved.listLoading || saved.listOffset === 0}
        onClick={() => void saved.loadExperiments(Math.max(0, saved.listOffset - 20))}><ArrowLeft size={18} /></button>
      <span>第 {Math.floor(saved.listOffset / 20) + 1} 页</span>
      <button className="icon-button" type="button" title="下一页实验" aria-label="下一页实验" disabled={saved.listLoading || saved.nextListOffset === null}
        onClick={() => { if (saved.nextListOffset !== null) void saved.loadExperiments(saved.nextListOffset) }}><ArrowRight size={18} /></button>
    </div>}
  </div>
})

function jobStatus(status: string): string {
  return { queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[status] ?? status
}

export const SavedResultViewer = observer(({ saved }: { saved: SavedResultsStore }) => {
  const viewerRef = useRef<HTMLDivElement>(null)
  const selection = saved.selection
  useEffect(() => {
    if (selection) viewerRef.current?.focus()
  }, [selection])
  if (!selection) return null
  const job = saved.job
  const image = saved.image
  const context = job?.parameters.experiment
  const isExperiment = selection.kind === 'experiment'
  const groupLabel = isExperiment ? context ? `第 ${context.ordinal} / ${context.total} 组` : '实验记录' : '历史图片'
  const placeholder = saved.loading ? '正在加载保存记录...'
    : saved.imageLoading ? '正在加载图片...'
      : saved.error ? '记录暂不可用，请查看下方信息。'
        : saved.imageError ? '这张图片已过期或暂不可用。'
          : job?.status === 'failed' ? '本组生成失败，参数和权重仍可查看。'
            : job?.status === 'queued' || job?.status === 'running' ? '任务尚未结束。服务器实验独立执行，可手动刷新查看结果。'
              : '图片已过期或没有保存的图片，参数和权重仍可查看。'

  function move(direction: -1 | 1) {
    void saved.move(direction)
    viewerRef.current?.focus({ preventScroll: true })
  }

  function close() {
    saved.close()
    document.getElementById('panel-toggle-history')?.focus({ preventScroll: true })
  }

  return <section id="saved-result-viewer" className="experiment-results saved-results" aria-labelledby="saved-result-title">
    <div className="section-heading">
      <div><span className="eyebrow">历史记录</span><h2 id="saved-result-title">{isExperiment ? '已保存的画风对比' : '已保存的图片'}</h2></div>
      <button className="icon-button" type="button" title="关闭历史图片" aria-label="关闭历史图片" onClick={close}><X size={18} /></button>
    </div>
    <p className="subtle">图片由服务器私有保存 7 天。关闭此视图只清除页面展示，不删除保存内容。</p>
    {saved.summary && <p className="subtle">已提交 {saved.summary.group_count} / {saved.summary.total} 组 · 已结束 {saved.summary.completed_count} 组 · 曾生成 {saved.summary.image_count} 张</p>}
    <article className="experiment-result-card">
      <figure className="experiment-image-item">
        <div className="experiment-image-viewer" role="group" aria-label="已保存图片切换" aria-describedby="saved-navigation-help"
          tabIndex={0} ref={viewerRef} onKeyDown={event => {
            if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
            if (event.target instanceof HTMLElement && event.target.closest('input, textarea, select, [contenteditable="true"]')) return
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
            event.preventDefault()
            move(event.key === 'ArrowLeft' ? -1 : 1)
          }}>
          <button className="icon-button experiment-image-arrow" type="button" title="上一个保存结果" aria-label="上一个保存结果"
            disabled={!saved.canPrevious} onClick={() => move(-1)}><ArrowLeft size={22} aria-hidden="true" /></button>
          <div className="experiment-image-frame" aria-busy={saved.loading || saved.imageLoading}>
            {image ? <img key={image.url} src={image.url} alt={`${groupLabel}，图像 ${image.index + 1}`} />
              : <p className="subtle" role="status">{placeholder}</p>}
          </div>
          <button className="icon-button experiment-image-arrow" type="button" title="下一个保存结果" aria-label="下一个保存结果"
            disabled={!saved.canNext} onClick={() => move(1)}><ArrowRight size={22} aria-hidden="true" /></button>
        </div>
        <figcaption>
          <span aria-live="polite" aria-atomic="true">{groupLabel}{job && (job.image_urls.length ? ` · 图像 ${saved.imageIndex + 1} / ${saved.imageSlots}` : ' · 无可用图片')}</span>
          {image && <a href={image.url} download={isExperiment ? `style-experiment-${image.filename}` : image.filename}
            className="icon-button" title="下载当前图片" aria-label="下载当前图片"><ArrowDownToLine size={17} aria-hidden="true" /></a>}
        </figcaption>
      </figure>
      <p className="prompt-hint" id="saved-navigation-help">左右箭头依次切换本组图片和下一个已保存组，聚焦图像区域后可按 ← / →。这里只查看保存结果，不改变草稿或服务器实验。</p>
      {(saved.error || saved.imageError) && <p className="alert" role="alert">{saved.error || saved.imageError}</p>}
      <div className="saved-result-actions"><button type="button" className="text-action" disabled={saved.loading || saved.imageLoading} onClick={() => void saved.retry()}>
        <RefreshCw size={15} aria-hidden="true" /> 刷新保存记录
      </button></div>
      {job && <>
        <div className="experiment-result-heading"><h3>{groupLabel}</h3>
          <span className={`status status-${job.status}`}>{jobStatus(job.status)}</span>
          <span>请求种子 {job.parameters.seed ?? '随机'}</span><span>实际种子 {job.effective_seed}</span>
        </div>
        {context && <ul className="experiment-result-weights" aria-label="保存的实验权重">{context.weights.map(weight =>
          <li key={weight.tag_index}><span>{weight.tag_index + 1}. {weight.label}</span><strong>{weight.weight}</strong></li>)}</ul>}
        {job.result_expires_at !== null && <p className="subtle saved-expiry">私有图片保存至 {new Date(job.result_expires_at * 1000).toLocaleString()}，查看不会延长保存时间。</p>}
        <details className="result-parameters"><summary>保存的完整生成参数</summary>
          <PromptSummary parameters={job.parameters} />
          {job.parameters.negative_prompt && <p>负向：{job.parameters.negative_prompt}</p>}
          <p>{job.parameters.model} · {job.parameters.width}×{job.parameters.height} · {job.parameters.sampler}</p>
          <p>{job.parameters.steps} 步 · CFG {job.parameters.cfg_scale} · 实际种子 {job.effective_seed} · {job.parameters.sample_count} 张 · {job.parameters.quality ? '高质量' : '标准质量'}</p>
          <p>任务 ID：{job.id}</p>
        </details>
        {job.error_code && <p className="alert" role="alert">{errorText(new ApiFailure(0, job.error_code, '生成失败，请检查服务状态。'))}</p>}
      </>}
    </article>
  </section>
})
