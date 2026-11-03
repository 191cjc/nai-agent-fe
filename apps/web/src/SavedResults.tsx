import { Suspense, useEffect, useRef, useState } from 'react'
import { observer } from 'mobx-react-lite'
import { ArrowLeft, ArrowRight, Ban, Download, FlaskConical, Images, Layers, RefreshCw, RotateCcw, UserRound, X } from 'lucide-react'
import { ApiFailure, errorText, type WorkspaceApi } from './api'
import { datasetItemText } from './dataset-run'
import { DatasetExportPanel } from './dataset-lazy'
import { GenerationParameters } from './GenerationParameters'
import type { SavedResultsStore } from './saved-results'
import { ImageSaveButton, ImageSeedButton } from './ImageActions'
import { preciseLabel } from './character-summary'

export const SavedExperimentList = observer(({ saved, api, onView }: { saved: SavedResultsStore; api: WorkspaceApi; onView: () => void }) => {
  const [exportingId, setExportingId] = useState<string | null>(null)
  // Multi-select export of several training sets into one zip.
  const [chosen, setChosen] = useState<readonly string[]>([])
  const [exportingChosen, setExportingChosen] = useState(false)
  return <div className="saved-experiment-list">
    <div className="history-toolbar"><span>已保存的画风实验与训练集</span>
      <button type="button" className="icon-button" title="刷新已保存实验" aria-label="刷新已保存实验" disabled={saved.listLoading}
        onClick={() => void saved.loadExperiments()}><RefreshCw size={17} /></button>
    </div>
    <p className="prompt-hint">新图像由服务器私有保存 7 天；参数和权重保留更久。刷新后可在这里重新对比，服务器实验的进度会在工作台接回。</p>
    {!saved.listLoaded && !saved.listLoading && <button className="secondary" type="button" onClick={() => void saved.loadExperiments(0)}>加载已保存实验</button>}
    {saved.listLoading && <p className="subtle" role="status">正在加载实验...</p>}
    {saved.listError && <p className="alert" role="alert">{saved.listError}</p>}
    {saved.listLoaded && !saved.listLoading && !saved.listError && !saved.experiments.length && <p className="subtle">暂无已保存的画风实验</p>}
    {chosen.length > 0 && <div className="history-selection">
      <span>已选 {chosen.length} 个训练集（可跨页）</span>
      <button className="text-action" type="button" disabled={exportingChosen} onClick={() => setExportingChosen(true)}><Download size={15} aria-hidden="true" /> 合并导出所选</button>
      <button className="text-action" type="button" disabled={exportingChosen} onClick={() => setChosen([])}>清除选择</button>
    </div>}
    {exportingChosen && chosen.length > 0 && <Suspense fallback={null}><DatasetExportPanel key={chosen.join(',')} api={api}
      source={{ kind: 'experiments', ids: chosen }} onClose={() => setExportingChosen(false)} /></Suspense>}
    <div className="history-list">{saved.experiments.map(experiment => <article className="history-item saved-experiment-item" key={experiment.id}>
      {experiment.kind === 'dataset' && <label className="history-select"><input type="checkbox" checked={chosen.includes(experiment.id)} disabled={exportingChosen}
        onChange={event => setChosen(current => event.target.checked ? [...current.filter(id => id !== experiment.id), experiment.id] : current.filter(id => id !== experiment.id))} /> 选入合并导出</label>}
      <time dateTime={new Date(experiment.created_at * 1000).toISOString()}>{new Date(experiment.created_at * 1000).toLocaleString()}</time>
      {experiment.kind === 'dataset' ? <>
        <p><Layers size={14} aria-hidden="true" /> 训练集批跑 · 已提交 <strong>{experiment.group_count}</strong> / {experiment.total} 条</p>
        <p className="history-meta">已结束 {experiment.completed_count} 条 · 曾生成 {experiment.image_count} 张（含已过期图像）</p>
      </> : <>
        <p>已提交 <strong>{experiment.group_count}</strong> / {experiment.total} 组</p>
        <p className="history-meta">已结束 {experiment.completed_count} 组 · 曾生成 {experiment.image_count} 张（含已过期图像）</p>
      </>}
      <div className="history-actions">
        <button className="text-action" type="button" onClick={() => { void saved.openExperiment(experiment.id); onView() }}>
          <FlaskConical size={15} aria-hidden="true" /> {experiment.kind === 'dataset' ? '浏览图片' : '打开对比'}
        </button>
        {experiment.kind === 'dataset' && <button className="text-action" type="button" aria-expanded={exportingId === experiment.id}
          onClick={() => setExportingId(exportingId === experiment.id ? null : experiment.id)}><Download size={15} aria-hidden="true" /> 导出训练集</button>}
      </div>
      {exportingId === experiment.id && <Suspense fallback={null}><DatasetExportPanel api={api} source={{ kind: 'experiment', id: experiment.id }} onClose={() => setExportingId(null)} /></Suspense>}
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

/** Thumbnails of the references a character group used; deleted references are omitted. */
function ReferenceThumbnails({ api, ids }: { api: WorkspaceApi; ids: string[] }) {
  const [urls, setUrls] = useState<string[]>([])
  const key = ids.join(',')
  useEffect(() => {
    const controller = new AbortController()
    const created: string[] = []
    void Promise.all(ids.map(id => api.referenceImage(id, controller.signal).then(blob => {
      const url = URL.createObjectURL(blob)
      created.push(url)
      return url
    }).catch(() => null))).then(loaded => {
      if (!controller.signal.aborted) setUrls(loaded.filter((url): url is string => url !== null))
    })
    return () => {
      controller.abort()
      created.forEach(url => URL.revokeObjectURL(url))
      setUrls([])
    }
    // ids are compared by value through key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, key])
  if (!urls.length) return null
  return <div className="reference-thumbnails" aria-label="本条使用的参考图">{urls.map(url => <img key={url} src={url} alt="参考图" />)}</div>
}

/** Copies the shown retained image into the owner's private reference images. */
function UseAsReferenceButton({ api, jobId, index }: { api: WorkspaceApi; jobId: string; index: number }) {
  const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [message, setMessage] = useState('')
  return <>
    <button className="text-action" type="button" disabled={state === 'saving' || state === 'saved'} onClick={() => {
      setState('saving')
      api.referenceFromResult(jobId, index).then(() => {
        setState('saved')
        setMessage('已加入参考图，可在「训练集批跑 → 角色训练集」中选择。')
      }).catch(error => {
        setState('error')
        setMessage(error instanceof ApiFailure ? errorText(error) : '设为参考图失败，请重试。')
      })
    }}><UserRound size={15} aria-hidden="true" /> {state === 'saved' ? '已设为参考图' : state === 'saving' ? '正在保存...' : '设为参考图'}</button>
    {message && <span className={state === 'error' ? 'alert' : 'subtle'} role="status">{message}</span>}
  </>
}

export const SavedResultViewer = observer(({ saved, api, onClose, onUseSeed, canSave }: {
  saved: SavedResultsStore
  api: WorkspaceApi
  onClose: () => void
  onUseSeed: (seed: number) => void
  canSave: () => boolean
}) => {
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
  const isDataset = context?.kind === 'dataset'
  const preloadLabel = {
    idle: '', reading: '正在读取实验记录', loading: '正在加载图片', completed: '本次加载检查已结束',
    cancelled: '已取消加载，已缓存图片仍可使用', capacity: '已达到缓存容量限制，后续图片尚未加载', error: '加载检查中断，可重新开始',
  }[saved.preloadStatus]
  const groupLabel = isExperiment ? context ? `第 ${context.ordinal} / ${context.total} ${isDataset ? '条' : '组'}` : '实验记录' : '历史图片'
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

  return <section id="saved-result-viewer" className="canvas-view saved-results" aria-labelledby="saved-result-title">
    <div className="canvas-toolbar">
      <div className="canvas-title"><FlaskConical size={16} aria-hidden="true" /><h2 id="saved-result-title">{isExperiment ? isDataset ? '已保存的训练集' : '已保存的画风对比' : '已保存的图片'}</h2>
        {job && <span className={`status status-${job.status}`}>{jobStatus(job.status)}</span>}
      </div>
      <div className="saved-viewer-toolbar-actions">
        {isExperiment && <button className="text-action saved-preload-button" type="button" aria-describedby="saved-preload-help"
          onClick={() => { if (saved.preloading) saved.cancelPreload(); else void saved.preloadImages() }}>
          {saved.preloading ? <X size={15} aria-hidden="true" /> : <Images size={15} aria-hidden="true" />}
          {saved.preloading ? '取消加载' : '加载全部图片'}
        </button>}
        <label className="history-select saved-review-toggle"><input type="checkbox" checked={saved.hideDiscarded}
          onChange={event => saved.setHideDiscarded(event.target.checked)} /> 只看未弃置</label>
        <button className="icon-button" type="button" title="关闭历史图片" aria-label="关闭历史图片" onClick={onClose}><X size={18} /></button>
      </div>
    </div>
      <figure className="canvas-figure">
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
            {image && job ? <><img key={image.url} src={image.url} alt={`${groupLabel}，图像 ${image.index + 1}`} className={saved.currentDiscarded ? 'discarded' : ''} />
              {saved.currentDiscarded && <span className="discarded-badge" role="status">已弃置 · 导出时不包含</span>}
              <ImageSeedButton seed={job.effective_seed} onUseSeed={onUseSeed} /></>
              : <div className="canvas-placeholder" role="status"><FlaskConical size={32} aria-hidden="true" /><p>{placeholder}</p></div>}
          </div>
          <button className="icon-button experiment-image-arrow" type="button" title="下一个保存结果" aria-label="下一个保存结果"
            disabled={!saved.canNext} onClick={() => move(1)}><ArrowRight size={22} aria-hidden="true" /></button>
        </div>
        <figcaption className="canvas-caption">
          <span aria-live="polite" aria-atomic="true">{groupLabel}{job && (job.image_urls.length ? ` · 图像 ${saved.imageIndex + 1} / ${saved.imageSlots}` : ' · 无可用图片')}</span>
          {image && job && <ImageSaveButton key={image.url} url={image.url} filename={isExperiment ? `style-experiment-${image.filename}` : image.filename}
            isCurrent={() => canSave() && saved.selection === selection && saved.job?.id === job.id && saved.image?.url === image.url} />}
          {image && job && <button className="text-action" type="button" disabled={saved.discardBusy}
            aria-pressed={saved.currentDiscarded} onClick={() => void saved.toggleDiscard()}>
            {saved.currentDiscarded ? <RotateCcw size={15} aria-hidden="true" /> : <Ban size={15} aria-hidden="true" />}
            {saved.discardBusy ? '正在保存...' : saved.currentDiscarded ? '恢复' : '弃置'}</button>}
          {image && job && <UseAsReferenceButton key={`${job.id}:${image.index}`} api={api} jobId={job.id} index={image.index} />}
        </figcaption>
      </figure>
    <div className="canvas-metadata">
      {isExperiment && <div className="saved-preload-info">
        {saved.preloadStatus !== 'idle' && <div className="saved-preload-status" role="status" aria-live="polite" aria-atomic="true">
          <strong>{preloadLabel}</strong>
          <span>已检查 {saved.preloadProcessedGroups} / {saved.preloadGroupLimit ?? '…'} 组 · 已处理 {saved.preloadProcessedImages} 张图片</span>
          <span>当前缓存 {saved.cachedImageCount} 张 / {(saved.cachedImageBytes / (1024 * 1024)).toFixed(1)} MiB · 跳过 {saved.preloadSkippedGroups} 组（无可用图片） · 图片失败 {saved.preloadFailedImages} 张</span>
        </div>}
        <p className="prompt-hint" id="saved-preload-help">加载全部图片会检查开始时已有的实验组，新增或未完成的结果可稍后再次加载。缓存最多 256 张 / 256 MiB，刷新页面或关闭对比后清空。</p>
        {saved.preloadError && <p className="alert" role="alert">{saved.preloadError}</p>}
        {saved.preloadImageError && <p className="saved-preload-image-error">最近一次图片加载失败：{saved.preloadImageError}（单张失败不会中断其余图片的加载）</p>}
      </div>}
      <p className="prompt-hint" id="saved-navigation-help">左右箭头依次切换本组图片和下一个已保存组，聚焦图像区域后可按 ← / →。点击图片右下角种子可填入生成设置；浏览不会启动生成或改变服务器实验。</p>
      {(saved.error || saved.imageError) && <p className="alert" role="alert">{saved.error || saved.imageError}</p>}
      {saved.discardError && <p className="alert" role="alert">弃置标记未保存：{saved.discardError}</p>}
      {job && (job.discarded_images?.length ?? 0) > 0 && <p className="subtle">本组已弃置 {job.discarded_images?.length} / {job.image_urls.length} 张（导出时跳过；可点「恢复」撤销）。</p>}
      <div className="saved-result-actions"><span className="prompt-hint">私有保存 7 天</span><button type="button" className="text-action" disabled={saved.loading || saved.imageLoading} onClick={() => void saved.retry()}>
        <RefreshCw size={15} aria-hidden="true" /> 刷新保存记录
      </button></div>
      {job && <>
        <div className="experiment-result-heading"><h3>{groupLabel}</h3>
          <span>请求种子 {job.parameters.seed ?? '随机'}</span><span>实际种子 {job.effective_seed}</span>
        </div>
        {context?.item && <p className="dataset-item-prompt" aria-label="训练集提示词">提示词：{datasetItemText(context.item)}</p>}
        {context?.item && job.parameters.reference && <p className="subtle">
          {job.parameters.reference.mode === 'gpt' ? `GPT 参考图生成 · ${job.parameters.model} · 质量 ${job.parameters.reference.gpt_quality ?? '自动'}` : job.parameters.reference.mode === 'vibe' ? `Vibe Transfer · 信息提取度 ${job.parameters.reference.information_extracted ?? 1} · 强度 ${job.parameters.reference.reference_strength ?? 1}` : job.parameters.reference.mode === 'precise' ? `精准参考 · ${preciseLabel(job.parameters.reference.precise_type)} · 强度 ${job.parameters.reference.precise_strength ?? 1} · 保真度 ${job.parameters.reference.precise_fidelity ?? 1}` : `图生图 strength ${job.parameters.reference.strength} · noise ${job.parameters.reference.noise}`}
          {' · '}画风：{job.parameters.style_prompt}</p>}
        {context?.item && job.parameters.reference && <ReferenceThumbnails api={api} ids={job.parameters.reference.images.map(image => image.id)} />}
        {context && context.weights.length > 0 && <ul className="experiment-result-weights" aria-label="保存的实验权重">{context.weights.map(weight =>
          <li key={weight.tag_index}><span>{weight.tag_index + 1}. {weight.label}</span><strong>{weight.weight}</strong></li>)}</ul>}
        {job.result_expires_at !== null && <p className="subtle saved-expiry">私有图片保存至 {new Date(job.result_expires_at * 1000).toLocaleString()}，查看不会延长保存时间。</p>}
        <details className="result-parameters"><summary>保存的完整生成参数</summary>
          {saved.summary && <p>已提交 {saved.summary.group_count} / {saved.summary.total} 组 · 已结束 {saved.summary.completed_count} 组 · 曾生成 {saved.summary.image_count} 张</p>}
          <GenerationParameters job={job} />
        </details>
        {job.error_code && <p className="alert" role="alert">{errorText(new ApiFailure(0, job.error_code, '生成失败，请检查服务状态。'))}</p>}
      </>}
    </div>
  </section>
})
