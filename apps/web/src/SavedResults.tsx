import { Suspense, useEffect, useRef, useState } from 'react'
import { observer } from 'mobx-react-lite'
import { ArrowLeft, ArrowRight, Ban, CheckSquare, Dices, Download, FlaskConical, Images, LayoutGrid, Layers, Pencil, RefreshCw, RotateCcw, Trash2, UserRound, X } from 'lucide-react'
import { ApiFailure, errorText, MAX_EXPERIMENT_NAME, type ExperimentRunState, type ExperimentSummary, type RerunEdits, type WorkspaceApi } from './api'
import { datasetItemText } from './dataset-run'
import { CaptionEditor, DatasetExportPanel, DatasetItemGloss, ReviewGrid } from './dataset-lazy'
import { GenerationParameters } from './GenerationParameters'
import type { SavedResultsStore } from './saved-results'
import { ImageSaveButton, ImageSeedButton } from './ImageActions'
import { preciseLabel } from './character-summary'
import { ReferenceThumb } from './ReferencePreview'

/** Name shown in confirmations; unnamed sets fall back to kind and creation time. */
function experimentLabel(experiment: ExperimentSummary): string {
  const kind = experiment.kind !== 'dataset' ? '画风实验' : experiment.dataset_type === 'character' ? '角色训练集' : '画风训练集'
  return experiment.name ? `「${experiment.name}」` : `未命名${kind}（${new Date(experiment.created_at * 1000).toLocaleString()}）`
}

export const SavedExperimentList = observer(({ saved, api, onView, activeIds = [] }: {
  saved: SavedResultsStore; api: WorkspaceApi; onView: () => void; activeIds?: readonly string[]
}) => {
  const [exportingId, setExportingId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteMessage, setDeleteMessage] = useState('')
  const [deleteError, setDeleteError] = useState('')
  // Labels of every set seen so far, so a cross-page batch confirmation can name them.
  const labels = useRef(new Map<string, string>())
  saved.experiments.forEach(experiment => labels.current.set(experiment.id, experimentLabel(experiment)))

  async function remove(ids: readonly string[]) {
    if (!ids.length || deleting) return
    const names = ids.map(id => labels.current.get(id) ?? id)
    const shown = names.length > 12 ? [...names.slice(0, 12), `……等共 ${names.length} 个`] : names
    if (!window.confirm(`确定永久删除以下 ${ids.length} 个实验/训练集？\n\n${shown.join('\n')}\n\n会删除全部生成记录、图片、弃置标记和名称，此操作无法撤销。参考图不会被删除。`)) return
    setDeleting(true)
    setDeleteMessage('')
    setDeleteError('')
    try {
      const result = await saved.deleteExperiments(ids)
      setChosen(current => current.filter(id => !result.deleted.includes(id)))
      if (result.deleted.includes(exportingId ?? '')) setExportingId(null)
      if (result.deleted.length) setDeleteMessage(`已删除 ${result.deleted.length} 个，共 ${result.groups} 条记录、${result.images} 张图片。`)
      if (result.failed.length) setDeleteError(`${result.failed.length} 个未删除：${result.failed.map(item => `${labels.current.get(item.id) ?? item.id} ${item.error}`).join('；')}`)
    } finally {
      setDeleting(false)
    }
  }

  // Multi-select export of several training sets into one zip.
  const [chosen, setChosen] = useState<readonly string[]>([])
  const [exportingChosen, setExportingChosen] = useState(false)
  const pageDatasetIds = saved.experiments.filter(experiment => experiment.kind === 'dataset').map(experiment => experiment.id)
  const allPageChosen = pageDatasetIds.length > 0 && pageDatasetIds.every(id => chosen.includes(id))
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
    {pageDatasetIds.length > 0 && <div className="history-selection merge-export-bar">
      <span>{chosen.length ? <>已选 <strong>{chosen.length}</strong> 个训练集（可跨页）</> : '勾选多个训练集，可合并导出到一个 zip'}</span>
      <button className="text-action" type="button" disabled={exportingChosen} onClick={() => setChosen(current => allPageChosen
        ? current.filter(id => !pageDatasetIds.includes(id))
        : [...current, ...pageDatasetIds.filter(id => !current.includes(id))])}>
        <CheckSquare size={15} aria-hidden="true" /> {allPageChosen ? '取消本页' : '全选本页训练集'}</button>
      <button className="text-action" type="button" disabled={exportingChosen || chosen.length === 0} onClick={() => setExportingChosen(true)}><Download size={15} aria-hidden="true" /> 合并导出所选{chosen.length ? `（${chosen.length}）` : ''}</button>
      <button className="text-action danger-text" type="button" disabled={exportingChosen || deleting || chosen.length === 0 || chosen.some(id => activeIds.includes(id))}
        title={chosen.some(id => activeIds.includes(id)) ? '所选中有正在运行或排队的训练集，结束或停止后可删除' : '永久删除所选训练集'}
        onClick={() => void remove(chosen)}><Trash2 size={15} aria-hidden="true" /> 删除所选{chosen.length ? `（${chosen.length}）` : ''}</button>
      {chosen.length > 0 && <button className="text-action" type="button" disabled={exportingChosen || deleting} onClick={() => setChosen([])}>清除选择</button>}
    </div>}
    {deleting && <p className="subtle" role="status">正在删除...</p>}
    {deleteMessage && <p className="experiment-note" role="status">{deleteMessage}</p>}
    {deleteError && <p className="alert" role="alert">{deleteError}</p>}
    {exportingChosen && chosen.length > 0 && <Suspense fallback={null}><DatasetExportPanel key={chosen.join(',')} api={api}
      source={{ kind: 'experiments', ids: chosen }} onClose={() => setExportingChosen(false)} /></Suspense>}
    <div className="history-list">{saved.experiments.map(experiment => <article className="history-item saved-experiment-item" key={experiment.id}>
      {experiment.kind === 'dataset' && experiment.cover_job_id && <ExperimentCover api={api} jobId={experiment.cover_job_id}
        label={experimentLabel(experiment)} onOpen={() => { void saved.openExperiment(experiment.id); onView() }} />}
      <div className="saved-experiment-body">
      {experiment.kind === 'dataset' && <label className="history-select"><input type="checkbox" checked={chosen.includes(experiment.id)} disabled={exportingChosen}
        onChange={event => setChosen(current => event.target.checked ? [...current.filter(id => id !== experiment.id), experiment.id] : current.filter(id => id !== experiment.id))} /> 选择</label>}
      {experiment.kind === 'dataset' && <ExperimentTitle saved={saved} experiment={experiment} />}
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
        <button className="icon-button danger" type="button" disabled={deleting || activeIds.includes(experiment.id)}
          title={activeIds.includes(experiment.id) ? '正在运行或排队，结束或停止后可删除' : '永久删除'}
          aria-label={`删除 ${experimentLabel(experiment)}`} onClick={() => void remove([experiment.id])}><Trash2 size={16} /></button>
      </div>
      </div>
      {exportingId === experiment.id && <Suspense fallback={null}><DatasetExportPanel api={api} source={{ kind: 'experiment', id: experiment.id }} fileName={experiment.name ?? undefined} onClose={() => setExportingId(null)} /></Suspense>}
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

const COVER_BUSY_RETRIES = 3

/** Training-set cover: thumbnail of its first succeeded image; hidden once expired or missing. */
function ExperimentCover({ api, jobId, label, onOpen }: {
  api: WorkspaceApi; jobId: string; label: string; onOpen: () => void
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    let owned: string | null = null
    setUrl(null)
    setFailed(false)
    void (async () => {
      for (let attempt = 0; ; attempt += 1) {
        try {
          const blob = await api.thumbnail(`/api/generation-results/${jobId}/images/0`, controller.signal)
          if (controller.signal.aborted) return
          owned = URL.createObjectURL(blob)
          setUrl(owned)
          return
        } catch (error) {
          if (controller.signal.aborted) return
          if (error instanceof ApiFailure && error.code === 'thumbnail_busy' && attempt < COVER_BUSY_RETRIES) {
            await new Promise(resolve => setTimeout(resolve, 800 * (attempt + 1)))
            continue
          }
          setFailed(true)
          return
        }
      }
    })()
    return () => {
      controller.abort()
      if (owned) URL.revokeObjectURL(owned)
    }
  }, [api, jobId])
  if (failed) return null
  return <button className="experiment-cover" type="button" title="浏览图片" aria-label={`浏览 ${label} 的图片`} onClick={onOpen}>
    {url ? <img src={url} alt="" /> : <span className="experiment-cover-placeholder" aria-hidden="true" />}
  </button>
}

/** 画风/角色 badge plus the owner's name, renamed in place. */
const ExperimentTitle = observer(({ saved, experiment }: { saved: SavedResultsStore; experiment: ExperimentSummary }) => {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const character = experiment.dataset_type === 'character'
  const label = experiment.name || '未命名训练集'
  async function save() {
    setSaving(true)
    setError('')
    try {
      await saved.renameExperiment(experiment.id, draft)
      setEditing(false)
    } catch (failure) {
      setError(errorText(failure))
    } finally {
      setSaving(false)
    }
  }
  return <div className="experiment-title">
    {experiment.dataset_type && <span className={`dataset-type-badge ${character ? 'character' : 'style'}`}>
      {character ? <UserRound size={12} aria-hidden="true" /> : <Layers size={12} aria-hidden="true" />} {character ? '角色' : '画风'}</span>}
    {editing ? <form className="experiment-rename" onSubmit={event => { event.preventDefault(); void save() }}>
      <input value={draft} maxLength={MAX_EXPERIMENT_NAME} autoFocus disabled={saving} aria-label="训练集名称" placeholder="留空则为未命名"
        onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Escape') setEditing(false) }} />
      <button className="text-action" type="submit" disabled={saving}>{saving ? '保存中...' : '保存'}</button>
      <button className="text-action" type="button" disabled={saving} onClick={() => setEditing(false)}>取消</button>
    </form> : <>
      <strong className={experiment.name ? '' : 'subtle'}>{label}</strong>
      <button className="icon-button" type="button" title="重命名" aria-label={`重命名 ${label}`}
        onClick={() => { setDraft(experiment.name ?? ''); setError(''); setEditing(true) }}><Pencil size={14} /></button>
    </>}
    {error && <span className="alert" role="alert">{error}</span>}
  </div>
})

function jobStatus(status: string): string {
  return { queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[status] ?? status
}

/** Thumbnails of the references a character group used; click one to view it full size. */
function ReferenceThumbnails({ api, ids }: { api: WorkspaceApi; ids: string[] }) {
  if (!ids.length) return null
  return <div className="reference-thumbnails" aria-label="本条使用的参考图">
    {ids.map((id, index) => <ReferenceThumb key={id} api={api} id={id} label={`参考图 ${index + 1}`} />)}
  </div>
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

export const SavedResultViewer = observer(({ saved, api, onClose, onUseSeed, canSave, onRerunQueued }: {
  saved: SavedResultsStore
  api: WorkspaceApi
  onClose: () => void
  onUseSeed: (seed: number) => void
  canSave: () => boolean
  /** A review-grid re-run batch joined the server queue. */
  onRerunQueued?: (run: ExperimentRunState) => void
}) => {
  const viewerRef = useRef<HTMLDivElement>(null)
  const selection = saved.selection
  const [gridFor, setGridFor] = useState<string | null>(null)
  // Single re-run editor: prefilled with this group's frozen item prompt and style.
  const [rerunEdit, setRerunEdit] = useState<{ jobId: string; prompt: string; style: string } | null>(null)
  useEffect(() => {
    if (selection) viewerRef.current?.focus()
  }, [selection])
  if (!selection) return null
  const datasetSelection = selection.kind === 'experiment' && saved.summary?.kind === 'dataset'
  const grid = datasetSelection && gridFor === selection.id
  const job = saved.job
  const image = saved.image
  const context = job?.parameters.experiment
  const isExperiment = selection.kind === 'experiment'
  const isDataset = context?.kind === 'dataset'
  const preloadLabel = {
    idle: '', reading: '正在读取实验记录', loading: '正在加载图片', completed: '本次加载检查已结束',
    cancelled: '已取消加载，已缓存图片仍可使用', capacity: '已达到缓存容量限制，后续图片尚未加载', error: '加载检查中断，可重新开始',
  }[saved.preloadStatus]
  const groupLabel = isExperiment ? context ? `第 ${context.ordinal} / ${context.total} ${isDataset ? '条' : '组'}${context.rerun_of ? '（重跑）' : ''}` : '实验记录' : '历史图片'
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
        {datasetSelection && <button className="text-action" type="button" aria-pressed={grid}
          title="一屏查看多张小预览，可多选重跑、按按钮弃置；适合筛训练集" onClick={() => setGridFor(grid ? null : selection.id)}>
          <LayoutGrid size={15} aria-hidden="true" /> {grid ? '单张查看' : '网格检查'}</button>}
        {isExperiment && !grid && <button className="text-action saved-preload-button" type="button" aria-describedby="saved-preload-help"
          onClick={() => { if (saved.preloading) saved.cancelPreload(); else void saved.preloadImages() }}>
          {saved.preloading ? <X size={15} aria-hidden="true" /> : <Images size={15} aria-hidden="true" />}
          {saved.preloading ? '取消加载' : '加载全部图片'}
        </button>}
        {!grid && <label className="history-select saved-review-toggle"><input type="checkbox" checked={saved.hideDiscarded}
          onChange={event => saved.setHideDiscarded(event.target.checked)} /> 只看未弃置</label>}
        <button className="icon-button" type="button" title="关闭历史图片" aria-label="关闭历史图片" onClick={onClose}><X size={18} /></button>
      </div>
    </div>
    {grid ? <Suspense fallback={<p className="subtle" role="status">正在打开网格检查…</p>}>
      <ReviewGrid api={api} experimentId={selection.id} setName={saved.summary?.name} onQueued={onRerunQueued} onClose={() => setGridFor(null)}
        onOpen={(offset, image) => { setGridFor(null); void saved.showGroup(offset, image) }} />
    </Suspense> : <>
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
          {saved.canRerun && <button className="text-action" type="button" disabled={saved.rerunBusy}
            title="同提示词、同参考图与设置，随机新种子再生成 1 张（一次付费生成）"
            onClick={() => setRerunEdit({ jobId: job?.id ?? '', prompt: job?.parameters.experiment?.item?.prompt ?? '', style: job?.parameters.style_prompt ?? '' })}>
            <Dices size={15} aria-hidden="true" /> {saved.rerunBusy ? '正在提交...' : '重跑（新种子）'}</button>}
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
      <p className="prompt-hint" id="saved-navigation-help">左右箭头依次切换本组图片和下一个已保存组，聚焦图像区域后可按 ← / →。点击图片右下角种子可填入生成设置；浏览不会启动生成，只有训练集里点「重跑（新种子）」并确认「提交重跑」才会提交一次付费生成，提交前可修改这一张的训练词和画风。</p>
      {(saved.error || saved.imageError) && <p className="alert" role="alert">{saved.error || saved.imageError}</p>}
      {saved.discardError && <p className="alert" role="alert">弃置标记未保存：{saved.discardError}</p>}
      {rerunEdit && job && rerunEdit.jobId === job.id && saved.canRerun && <div className="rerun-batch" role="group" aria-label="重跑设置">
        <p><strong>重跑 1 张</strong>（新随机种子，一次付费生成{image !== null && !saved.currentDiscarded ? '；当前图片会被标记弃置，可随时恢复' : ''}）。改过的训练词会成为新图的 caption{job.parameters.experiment?.item?.characters?.length ? '；多人条目只改共享场景' : ''}。</p>
        <label className="field"><span>训练词</span>
          <textarea rows={3} value={rerunEdit.prompt} maxLength={1000} spellCheck={false}
            onChange={event => setRerunEdit({ ...rerunEdit, prompt: event.target.value })} /></label>
        <label className="field"><span>画风</span>
          <textarea rows={3} value={rerunEdit.style} maxLength={3000} spellCheck={false}
            onChange={event => setRerunEdit({ ...rerunEdit, style: event.target.value })} /></label>
        <div className="rerun-batch-actions">
          <button type="button" disabled={saved.rerunBusy || !rerunEdit.prompt.trim() || !rerunEdit.style.trim()} onClick={() => {
            const item = job.parameters.experiment?.item?.prompt
            const edits: RerunEdits = {
              ...(rerunEdit.prompt !== item ? { prompt: rerunEdit.prompt } : {}),
              ...(rerunEdit.style !== job.parameters.style_prompt ? { style_prompt: rerunEdit.style } : {}),
            }
            setRerunEdit(null)
            void saved.rerunCurrent(edits)
          }}><Dices size={14} aria-hidden="true" /> 提交重跑</button>
          <button className="secondary" type="button" onClick={() => setRerunEdit(null)}>取消</button>
        </div>
      </div>}
      {saved.rerunMessage && <p className="subtle" role="status">{saved.rerunMessage}</p>}
      {saved.rerunError && <p className="alert" role="alert">重跑未提交：{saved.rerunError}</p>}
      {job && (job.discarded_images?.length ?? 0) > 0 && <p className="subtle">本组已弃置 {job.discarded_images?.length} / {job.image_urls.length} 张（导出时跳过；可点「恢复」撤销）。</p>}
      <div className="saved-result-actions"><span className="prompt-hint">私有保存 7 天</span><button type="button" className="text-action" disabled={saved.loading || saved.imageLoading} onClick={() => void saved.retry()}>
        <RefreshCw size={15} aria-hidden="true" /> 刷新保存记录
      </button></div>
      {job && <>
        <div className="experiment-result-heading"><h3>{groupLabel}</h3>
          <span>请求种子 {job.parameters.seed ?? '随机'}</span><span>实际种子 {job.effective_seed}</span>
        </div>
        {context?.item && <p className="dataset-item-prompt" aria-label="训练集提示词">提示词：{datasetItemText(context.item)}</p>}
        {context?.item && <Suspense fallback={null}><DatasetItemGloss item={context.item} style={job.parameters.style_prompt} /></Suspense>}
        {isDataset && <Suspense fallback={null}><CaptionEditor key={job.id} job={job} saved={saved} /></Suspense>}
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
    </>}
  </section>
})
