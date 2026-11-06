import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Ban, CheckSquare, Dices, Maximize2, PencilLine, RefreshCw, Square, Undo2, X } from 'lucide-react'
import { ApiFailure, errorText, type ExperimentRunState, type GenerationView, type RerunBatchItem, type WorkspaceApi } from './api'
import { DATASET_CATEGORIES } from './dataset-prompts'
import { CHARACTER_CATEGORIES } from './character-prompts'
import { translatePrompt } from './prompt-zh'
import { contentCaption } from './dataset-export'
import { datasetItemZh } from './PromptGloss'

/** Tiles per page: bounds preview requests and Blob memory (~60 × 30 KB). */
const PAGE_SIZE = 60
const METADATA_PAGE = 100
const MAX_GROUPS = 3000
const PREVIEW_CONCURRENCY = 4
const BUSY_RETRIES = 3

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries([
  ...DATASET_CATEGORIES.map(category => [category.id, category.label]),
  ...CHARACTER_CATEGORIES.map(category => [category.id, category.label]),
  ['custom', '自定义'],
])

interface Tile {
  key: string
  offset: number
  job: GenerationView
  index: number | null
  category: string
}

function categoryOf(job: GenerationView): string {
  const id = job.parameters.experiment?.item?.id ?? ''
  return id.replace(/-\d+$/, '') || 'custom'
}

function ordinalLabel(job: GenerationView): string {
  const context = job.parameters.experiment
  return `第 ${context?.ordinal ?? '?'} 条${context?.rerun_of ? '（重跑）' : ''}`
}

/** Re-runs already made from each source group. */
export function rerunCounts(groups: readonly GenerationView[]): Map<string, number> {
  const reruns = new Map<string, number>()
  for (const group of groups) {
    const source = group.parameters.experiment?.rerun_of
    if (source) reruns.set(source, (reruns.get(source) ?? 0) + 1)
  }
  return reruns
}

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    signal.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')) }, { once: true })
  })
}

export type CaptionOperation =
  | { kind: 'replace'; find: string; replace: string }
  | { kind: 'prefix'; text: string }
  | { kind: 'suffix'; text: string }
  | { kind: 'reset' }

/** Training caption after one bulk operation; null = back to the derived caption. */
export function applyCaptionOperation(current: string, operation: CaptionOperation): string | null {
  const tidy = (text: string) => text.trim().replace(/^[,\s]+|[,\s]+$/g, '')
  switch (operation.kind) {
    case 'reset': return null
    case 'replace': return tidy(current.split(operation.find).join(operation.replace))
    case 'prefix': return [tidy(operation.text), tidy(current)].filter(Boolean).join(', ')
    case 'suffix': return [tidy(current), tidy(operation.text)].filter(Boolean).join(', ')
  }
}

/** Sources of this set's unfinished re-run batches the server has not submitted yet. */
export function queuedRerunSources(runs: readonly ExperimentRunState[], experimentId: string): Map<string, number> {
  const queued = new Map<string, number>()
  for (const run of runs) {
    if (run.kind !== 'rerun' || run.rerun_experiment_id !== experimentId || run.status !== 'running') continue
    for (const item of (run.rerun_items ?? []).slice(Number(run.next_ordinal) - 1)) queued.set(item.job_id, (queued.get(item.job_id) ?? 0) + 1)
  }
  return queued
}

export function ReviewGrid({ api, experimentId, setName, onQueued, onOpen, onClose }: {
  api: WorkspaceApi
  experimentId: string
  /** Training-set name, used to label its re-run batches in the queue. */
  setName?: string | null
  /** A re-run batch was accepted: show it in the run queue. */
  onQueued?: (run: ExperimentRunState) => void
  /** Opens the full-size viewer at this group offset and image index. */
  onOpen: (offset: number, image: number) => void
  onClose: () => void
}) {
  const [groups, setGroups] = useState<GenerationView[] | null>(null)
  const [loadError, setLoadError] = useState('')
  const [reload, setReload] = useState(0)
  const [category, setCategory] = useState('all')
  const [hideDiscarded, setHideDiscarded] = useState(false)
  const [page, setPage] = useState(0)
  const [previews, setPreviews] = useState<Record<string, string | 'error'>>({})
  const [busyKeys, setBusyKeys] = useState<ReadonlySet<string>>(new Set())
  const [actionError, setActionError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // Not-yet-submitted sources of this set's server-side re-run batches (by source job id).
  const [queued, setQueued] = useState<ReadonlyMap<string, number>>(new Map())
  // Bulk training-caption editor (training only, never generates).
  const [captionEdit, setCaptionEdit] = useState<{ scope: 'selected' | 'visible' | 'all'; kind: CaptionOperation['kind']; find: string; text: string } | null>(null)
  const [captionBusy, setCaptionBusy] = useState(false)
  const [rerunMessage, setRerunMessage] = useState('')
  // Selected tiles by key; kept across pages, category and discard filters until submitted or cleared.
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  // Batch editor over the selected tiles: one optional new style, an editable prompt per tile.
  // `id` is reused after an unknown outcome so a resubmission cannot queue the batch twice.
  const [batch, setBatch] = useState<{ id: string; sources: Tile[]; prompts: string[]; style: string; discardReplaced: boolean } | null>(null)
  const scrollRef = useRef<HTMLElement | null>(null)

  // Metadata only (no image bytes): bounded pages in server order.
  useEffect(() => {
    const controller = new AbortController()
    setGroups(null)
    setLoadError('')
    void (async () => {
      const loaded: GenerationView[] = []
      let offset: number | null = 0
      while (offset !== null && loaded.length < MAX_GROUPS) {
        const result = await api.experiment(experimentId, offset, METADATA_PAGE, controller.signal)
        loaded.push(...result.items)
        offset = result.next_offset
      }
      if (!controller.signal.aborted) setGroups(loaded)
    })().catch(error => { if (!controller.signal.aborted) setLoadError(errorText(error)) })
    // Best effort: without the queue, quick picks just cannot exclude batched sources.
    void api.queuedExperimentRuns(controller.signal)
      .then(runs => { if (!controller.signal.aborted) setQueued(queuedRerunSources(runs, experimentId)) })
      .catch(() => undefined)
    return () => controller.abort()
  }, [api, experimentId, reload])

  const tiles = useMemo<Tile[]>(() => (groups ?? []).flatMap((job, offset): Tile[] => {
    const base = { offset, job, category: categoryOf(job) }
    if (job.status !== 'succeeded' || !job.image_urls.length) return [{ ...base, key: `${job.id}:x`, index: null }]
    return job.image_urls.map((_url, index) => ({ ...base, key: `${job.id}:${index}`, index }))
  }), [groups])
  const categories = useMemo(() => [...new Set(tiles.map(tile => tile.category))], [tiles])
  const visible = useMemo(() => tiles.filter(tile => (category === 'all' || tile.category === category)
    && !(hideDiscarded && tile.index !== null && tile.job.discarded_images?.includes(tile.index))), [tiles, category, hideDiscarded])
  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE))
  const current = Math.min(page, pages - 1)
  useEffect(() => { scrollRef.current?.scrollTo({ top: 0 }) }, [current])
  const shown = useMemo(() => visible.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE), [visible, current])
  const shownPaths = shown.flatMap(tile => tile.index === null ? [] : [{ key: tile.key, path: tile.job.image_urls[tile.index] }])
  const pathKey = shownPaths.map(item => item.key).join('|')
  const discardedCount = tiles.filter(tile => tile.index !== null && tile.job.discarded_images?.includes(tile.index)).length
  const failedCount = (groups ?? []).filter(group => group.status === 'failed').length
  const reruns = useMemo(() => rerunCounts(groups ?? []), [groups])
  // Made plus still queued on the server: what quick picks treat as already replaced.
  const replaced = useMemo(() => {
    const counts = new Map(reruns)
    queued.forEach((count, id) => counts.set(id, (counts.get(id) ?? 0) + count))
    return counts
  }, [reruns, queued])
  const queuedCount = [...queued.values()].reduce((sum, count) => sum + count, 0)
  // A reload drops selections whose tile no longer exists (e.g. an image expired).
  useEffect(() => {
    if (!groups) return
    const keys = new Set(tiles.map(tile => tile.key))
    setSelected(current => [...current].every(key => keys.has(key)) ? current : new Set([...current].filter(key => keys.has(key))))
  }, [groups, tiles])
  const selectedTiles = useMemo(() => tiles.filter(tile => selected.has(tile.key)), [tiles, selected])
  const hiddenSelected = selectedTiles.length - selectedTiles.filter(tile => visible.includes(tile)).length
  // Quick picks select only what still needs a replacement, so nothing is paid for twice.
  const pendingFailedTiles = useMemo(() => tiles.filter(tile => tile.job.status === 'failed' && !(replaced.get(tile.job.id) ?? 0)), [tiles, replaced])
  const pendingDiscardedTiles = useMemo(() => (groups ?? []).flatMap(group => {
    if (group.status !== 'succeeded') return []
    const marks = [...(group.discarded_images ?? [])].sort((left, right) => left - right)
    const remaining = Math.max(0, marks.length - (replaced.get(group.id) ?? 0))
    return marks.slice(0, remaining).map(index => `${group.id}:${index}`)
  }), [groups, replaced])

  // Groups (not images) a bulk caption edit touches: succeeded groups of the chosen tiles.
  const captionPlan = useMemo(() => {
    if (!captionEdit) return null
    const scoped = captionEdit.scope === 'selected' ? selectedTiles : captionEdit.scope === 'visible' ? visible : tiles
    const jobs = [...new Map(scoped.filter(tile => tile.job.status === 'succeeded').map(tile => [tile.job.id, tile.job])).values()]
    const operation: CaptionOperation | null = captionEdit.kind === 'replace'
      ? (captionEdit.find ? { kind: 'replace', find: captionEdit.find, replace: captionEdit.text } : null)
      : captionEdit.kind === 'reset' ? { kind: 'reset' }
        : (captionEdit.text.trim() ? { kind: captionEdit.kind, text: captionEdit.text } : null)
    const changes: { job: GenerationView; before: string; after: string | null }[] = []
    let blank = 0
    if (operation) for (const job of jobs) {
      const before = contentCaption(job.parameters, job.caption_override)
      const after = applyCaptionOperation(before, operation)
      if (after === '') { blank += 1; continue }
      if (after === null ? job.caption_override == null : after === before) continue
      changes.push({ job, before, after })
    }
    return { jobs: jobs.length, ready: operation !== null, changes, blank }
  }, [captionEdit, selectedTiles, visible, tiles])

  // Previews for the shown page only; every Blob URL is revoked when the page changes.
  useEffect(() => {
    const controller = new AbortController()
    const owned: string[] = []
    const queue = [...shownPaths]
    setPreviews({})
    async function worker() {
      for (let item = queue.shift(); item && !controller.signal.aborted; item = queue.shift()) {
        const { key, path } = item
        for (let attempt = 0; ; attempt += 1) {
          try {
            const blob = await api.thumbnail(path, controller.signal)
            if (controller.signal.aborted) return
            const url = URL.createObjectURL(blob)
            owned.push(url)
            setPreviews(currentPreviews => ({ ...currentPreviews, [key]: url }))
            break
          } catch (error) {
            if (controller.signal.aborted) return
            if (error instanceof ApiFailure && error.code === 'thumbnail_busy' && attempt < BUSY_RETRIES) {
              await wait(800 * (attempt + 1), controller.signal).catch(() => undefined)
              continue
            }
            setPreviews(currentPreviews => ({ ...currentPreviews, [key]: 'error' }))
            break
          }
        }
      }
    }
    void Promise.all(Array.from({ length: PREVIEW_CONCURRENCY }, worker))
    return () => {
      controller.abort()
      owned.forEach(url => URL.revokeObjectURL(url))
    }
    // shownPaths is derived from pathKey; re-running on identity changes would refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, pathKey])

  const toggle = useCallback(async (tile: Tile) => {
    if (tile.index === null || busyKeys.has(tile.key)) return
    const index = tile.index
    const discarded = !tile.job.discarded_images?.includes(index)
    setBusyKeys(keys => new Set(keys).add(tile.key))
    setActionError('')
    try {
      await api.setImageDiscarded(tile.job.id, index, discarded)
      setGroups(currentGroups => currentGroups?.map(group => {
        if (group.id !== tile.job.id) return group
        const marks = new Set(group.discarded_images ?? [])
        if (discarded) marks.add(index)
        else marks.delete(index)
        return { ...group, discarded_images: [...marks].sort((left, right) => left - right) }
      }) ?? null)
    } catch (error) {
      setActionError(`${ordinalLabel(tile.job)}标记未保存：${errorText(error)}`)
    } finally {
      setBusyKeys(keys => { const next = new Set(keys); next.delete(tile.key); return next })
    }
  }, [api, busyKeys])

  function selectKeys(keys: readonly string[], value = true) {
    setSelected(current => {
      const next = new Set(current)
      keys.forEach(key => { if (value) next.add(key); else next.delete(key) })
      return next
    })
  }

  function newBatchId(): string | null {
    try { return crypto.randomUUID() } catch {
      setActionError('浏览器无法创建批次编号，请通过 HTTPS 使用支持的浏览器。')
      return null
    }
  }

  function openBatch() {
    if (!selectedTiles.length || submitting) return
    const id = newBatchId()
    if (!id) return
    setRerunMessage('')
    setBatch({ id, sources: selectedTiles, prompts: selectedTiles.map(tile => tile.job.parameters.experiment?.item?.prompt ?? ''), style: '', discardReplaced: true })
  }

  async function rerunAll() {
    if (!batch || submitting) return
    const { id, sources, prompts, style, discardReplaced } = batch
    if (prompts.some(prompt => !prompt.trim())) { setActionError('训练词不能为空。'); return }
    const repeated = sources.filter(tile => replaced.get(tile.job.id)).length
    if (!window.confirm(`为所选 ${sources.length} 张各重跑 1 张（新随机种子${style.trim() ? '，使用新画风' : '，保持原画风'}）？这是 ${sources.length} 次付费生成。\n会作为一个任务加入服务器队列，在后台按顺序生成，提交后可以关闭页面。${repeated ? `\n其中 ${repeated} 张所在条目以前已经重跑过或正在排队重跑。` : ''}`)) return
    const items: RerunBatchItem[] = sources.map((tile, index) => {
      const source = tile.job
      // Replacing a kept image marks it discarded when the server submits its re-run.
      const discard = discardReplaced && tile.index !== null && !source.discarded_images?.includes(tile.index)
      return {
        job_id: source.id,
        ...(discard && tile.index !== null ? { discard_index: tile.index } : {}),
        ...(prompts[index] !== source.parameters.experiment?.item?.prompt ? { prompt: prompts[index] } : {}),
        ...(style.trim() ? { style_prompt: style } : {}),
      }
    })
    const name = `${(setName || '训练集').slice(0, 72)} · 重跑`
    setSubmitting(true)
    setRerunMessage('')
    setActionError('')
    try {
      const run = await api.createRerunBatch({ id, experiment_id: experimentId, items, name })
      selectKeys(sources.map(tile => tile.key), false)
      setBatch(null)
      onQueued?.(run)
      setRerunMessage(`已加入服务器队列：${sources.length} 张${run.queue_position ? `，前面还有 ${run.queue_position} 个任务` : '，马上开始'}。可以关闭页面，进度见「实验与训练集队列」；生成完成后点「刷新」查看新图。`)
      setReload(value => value + 1)
    } catch (error) {
      const definite = error instanceof ApiFailure && error.status >= 400 && error.status < 500
      if (definite) {
        // Not accepted: a later submission is a new batch.
        const next = newBatchId()
        if (next) setBatch(current => current && { ...current, id: next })
        setActionError(`重跑未加入队列：${errorText(error)}`)
      } else {
        // Possibly accepted: resubmitting the unchanged batch returns it instead of queueing twice.
        setActionError(`提交结果未知：${errorText(error)} 请先在「实验与训练集队列」核对；不修改内容直接再点「加入队列」不会重复排队。`)
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function applyCaptions() {
    if (!captionPlan || !captionPlan.changes.length || captionBusy) return
    const { changes } = captionPlan
    if (!window.confirm(`修改 ${changes.length} 条的训练词？只影响导出的 caption，不会重新生成。可再用「恢复默认」撤销。`)) return
    setCaptionBusy(true)
    setActionError('')
    setRerunMessage('')
    let saved = 0
    try {
      for (let start = 0; start < changes.length; start += 3000) {
        const chunk = changes.slice(start, start + 3000)
        await api.setCaptions(experimentId, chunk.map(change => ({ job_id: change.job.id, caption: change.after })))
        const updated = new Map(chunk.map(change => [change.job.id, change.after]))
        setGroups(current => current?.map(group => updated.has(group.id) ? { ...group, caption_override: updated.get(group.id) ?? null } : group) ?? null)
        saved += chunk.length
      }
      setCaptionEdit(null)
      setRerunMessage(`已修改 ${saved} 条的训练词（只影响导出）。`)
    } catch (error) {
      setActionError(`训练词修改在第 ${saved + 1} 条处停止（已保存 ${saved} 条）：${errorText(error)}`)
    } finally {
      setCaptionBusy(false)
    }
  }

  return <section ref={scrollRef} className="review-grid" aria-label="网格检查">
    <div className="review-grid-toolbar">
      <label className="field review-grid-filter"><span>分类</span>
        <select value={category} onChange={event => { setCategory(event.target.value); setPage(0) }}>
          <option value="all">全部（{tiles.length}）</option>
          {categories.map(id => <option key={id} value={id}>{CATEGORY_LABELS[id] ?? id}（{tiles.filter(tile => tile.category === id).length}）</option>)}
        </select></label>
      <label className="history-select"><input type="checkbox" checked={hideDiscarded} onChange={event => { setHideDiscarded(event.target.checked); setPage(0) }} /> 隐藏已弃置</label>
      <span className="subtle" role="status">已弃置 {discardedCount} 张 · 失败 {failedCount} 条</span>
      {queuedCount > 0 && <span className="subtle" role="status">排队中的重跑 {queuedCount} 张</span>}
      <button className="text-action" type="button" disabled={!groups || submitting} onClick={() => setReload(value => value + 1)}><RefreshCw size={14} aria-hidden="true" /> 刷新</button>
      <button className="text-action" type="button" disabled={!selectedTiles.length || batch !== null || submitting} title="为所选图片各重跑 1 张；可先改画风和训练词"
        onClick={openBatch}><Dices size={14} aria-hidden="true" /> 重跑所选（{selectedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!groups || captionEdit !== null || captionBusy} title="对已选、当前筛选或全部条目的训练词做替换、加前缀、加后缀；只影响导出"
        onClick={() => setCaptionEdit({ scope: selectedTiles.length ? 'selected' : 'all', kind: 'replace', find: '', text: '' })}><PencilLine size={14} aria-hidden="true" /> 批量改训练词</button>
      <button className="icon-button" type="button" title="返回单张查看" aria-label="返回单张查看" onClick={onClose}><X size={18} /></button>
    </div>
    {groups && <div className="review-grid-selection" role="group" aria-label="多选">
      <span role="status">已选 <strong>{selectedTiles.length}</strong> 张{hiddenSelected > 0 ? `（${hiddenSelected} 张不在当前筛选中）` : ''}</span>
      <button className="text-action" type="button" disabled={!pendingFailedTiles.length || batch !== null} title="生成失败、还没补跑过也不在重跑队列中的条目"
        onClick={() => selectKeys(pendingFailedTiles.map(tile => tile.key))}>选择全部失败（{pendingFailedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!pendingDiscardedTiles.length || batch !== null} title="已弃置、还没重跑过也不在重跑队列中的图片"
        onClick={() => selectKeys(pendingDiscardedTiles)}>选择全部已弃置（{pendingDiscardedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!shown.length || batch !== null} onClick={() => selectKeys(shown.map(tile => tile.key))}>选择本页</button>
      <button className="text-action" type="button" disabled={!visible.length || batch !== null} title="当前分类和筛选下的全部图片（所有页）"
        onClick={() => selectKeys(visible.map(tile => tile.key))}>选择筛选结果（{visible.length}）</button>
      <button className="text-action" type="button" disabled={!selected.size || batch !== null} onClick={() => setSelected(new Set())}>清空选择</button>
    </div>}
    <p className="prompt-hint">点图片选择或取消选择，点右上角 ⊘ 按钮弃置或恢复（导出时跳过已弃置）；多选后「重跑所选」，翻页和切换分类不会丢失已选；点右上角放大按钮查看原图。每页 {PAGE_SIZE} 张，只加载小尺寸预览，不占用原图缓存。</p>
    {loadError && <p className="alert" role="alert">记录读取失败：{loadError}</p>}
    {actionError && <p className="alert" role="alert">{actionError}</p>}
    {rerunMessage && <p className="subtle" role="status">{rerunMessage}</p>}
    {captionEdit && captionPlan && <div className="rerun-batch" role="group" aria-label="批量改训练词">
      <p><strong>批量改训练词</strong>：只改导出的 caption（内容标签部分），不重新生成、不付费。触发词、导出前缀和角色训练集的画风仍在导出时自动加在最前面。失败的条目没有图片，不处理。</p>
      <div className="caption-bulk-row" role="radiogroup" aria-label="范围">
        <span>范围</span>
        {([['selected', `已选（${new Set(selectedTiles.map(tile => tile.job.id)).size} 条）`], ['visible', `当前筛选（${new Set(visible.map(tile => tile.job.id)).size} 条）`], ['all', `全部（${groups?.length ?? 0} 条）`]] as const).map(([value, label]) =>
          <label key={value} className="history-select"><input type="radio" name="caption-scope" checked={captionEdit.scope === value} disabled={captionBusy}
            onChange={() => setCaptionEdit({ ...captionEdit, scope: value })} /> {label}</label>)}
      </div>
      <div className="caption-bulk-row" role="radiogroup" aria-label="操作">
        <span>操作</span>
        {([['replace', '文本替换'], ['prefix', '加前缀'], ['suffix', '加后缀'], ['reset', '恢复默认']] as const).map(([value, label]) =>
          <label key={value} className="history-select"><input type="radio" name="caption-kind" checked={captionEdit.kind === value} disabled={captionBusy}
            onChange={() => setCaptionEdit({ ...captionEdit, kind: value })} /> {label}</label>)}
      </div>
      {captionEdit.kind === 'replace' && <div className="caption-bulk-fields">
        <label className="field"><span>查找（区分大小写，替换全部出现处）</span>
          <input type="text" value={captionEdit.find} maxLength={1000} spellCheck={false} disabled={captionBusy}
            onChange={event => setCaptionEdit({ ...captionEdit, find: event.target.value })} /></label>
        <label className="field"><span>替换为（留空即删除）</span>
          <input type="text" value={captionEdit.text} maxLength={1000} spellCheck={false} disabled={captionBusy}
            onChange={event => setCaptionEdit({ ...captionEdit, text: event.target.value })} /></label>
      </div>}
      {(captionEdit.kind === 'prefix' || captionEdit.kind === 'suffix') && <label className="field">
        <span>{captionEdit.kind === 'prefix' ? '加在训练词最前面' : '加在训练词最后面'}（用逗号分隔多个标签）</span>
        <input type="text" value={captionEdit.text} maxLength={1000} spellCheck={false} disabled={captionBusy}
          onChange={event => setCaptionEdit({ ...captionEdit, text: event.target.value })} /></label>}
      {captionEdit.kind === 'reset' && <p className="prompt-hint">把范围内改过的训练词恢复为由提示词自动生成的训练词。</p>}
      <p role="status">{captionPlan.ready ? `范围内 ${captionPlan.jobs} 条成功条目，将修改 ${captionPlan.changes.length} 条${captionPlan.blank ? `；${captionPlan.blank} 条改完会变空，已跳过` : ''}。` : '填写内容后显示预览。'}</p>
      {captionPlan.changes.length > 0 && <ol className="caption-bulk-preview">{captionPlan.changes.slice(0, 3).map(change => <li key={change.job.id}>
        <span>{ordinalLabel(change.job)}</span><span className="subtle">原：{change.before}</span><span>新：{change.after ?? contentCaption(change.job.parameters)}</span>
      </li>)}</ol>}
      <div className="rerun-batch-actions">
        <button type="button" disabled={captionBusy || !captionPlan.changes.length} onClick={() => void applyCaptions()}>
          <PencilLine size={14} aria-hidden="true" /> {captionBusy ? '正在保存...' : `修改 ${captionPlan.changes.length} 条`}</button>
        <button className="secondary" type="button" disabled={captionBusy} onClick={() => setCaptionEdit(null)}>取消</button>
      </div>
    </div>}
    {batch && <div className="rerun-batch" role="group" aria-label="批量重跑设置">
      <p><strong>重跑所选 {batch.sources.length} 张</strong>：每张 1 次付费生成，新随机种子。改过的训练词会成为新图的 caption。整批作为一个任务加入服务器队列（和训练集同一队列，按顺序执行），提交后可以关闭页面；可在队列中停止或继续。</p>
      <label className="field"><span>新画风（留空则每张保持原来的画风）</span>
        <textarea rows={2} value={batch.style} maxLength={3000} spellCheck={false}
          onChange={event => setBatch({ ...batch, style: event.target.value })} /></label>
      <label className="history-select"><input type="checkbox" checked={batch.discardReplaced}
        onChange={event => setBatch({ ...batch, discardReplaced: event.target.checked })} /> 开始重跑某张时弃置被替换的原图（只影响还没弃置的成功图片）</label>
      <ol className="rerun-batch-items">{batch.sources.map((tile, index) => <li key={tile.key}>
        <span>{ordinalLabel(tile.job)}{tile.index !== null && tile.job.image_urls.length > 1 ? ` · ${tile.index + 1}` : ''}{tile.job.status === 'failed' ? '（失败）' : tile.index !== null && tile.job.discarded_images?.includes(tile.index) ? '（已弃置）' : ''}{reruns.get(tile.job.id) ? `（已重跑 ${reruns.get(tile.job.id)} 次）` : ''}{queued.get(tile.job.id) ? `（重跑排队中 ${queued.get(tile.job.id)} 张）` : ''}{tile.job.parameters.experiment?.item?.characters?.length ? '（多人：只改共享场景）' : ''}</span>
        <textarea rows={2} value={batch.prompts[index]} maxLength={1000} spellCheck={false} aria-label={`${ordinalLabel(tile.job)}的训练词`}
          onChange={event => setBatch({ ...batch, prompts: batch.prompts.map((value, at) => at === index ? event.target.value : value) })} />
        <span className="dataset-item-zh">{translatePrompt(batch.prompts[index])}</span>
      </li>)}</ol>
      <div className="rerun-batch-actions">
        <button type="button" disabled={submitting} onClick={() => void rerunAll()}><Dices size={14} aria-hidden="true" /> {submitting ? '正在加入队列...' : `加入队列（${batch.sources.length} 张）`}</button>
        <button className="secondary" type="button" disabled={submitting} onClick={() => setBatch(null)}>取消</button>
      </div>
    </div>}
    {!groups && !loadError && <p className="subtle" role="status">正在读取训练集记录…</p>}
    {groups && <ul className="review-grid-tiles">{shown.map(tile => {
      const discarded = tile.index !== null && tile.job.discarded_images?.includes(tile.index) === true
      const preview = previews[tile.key]
      const item = tile.job.parameters.experiment?.item
      const override = tile.job.caption_override ?? null
      const prompt = override ?? item?.prompt ?? ''
      const zh = override ? translatePrompt(override) : item ? datasetItemZh(item) : ''
      const chosen = selected.has(tile.key)
      return <li key={tile.key} className={`${discarded ? 'discarded' : ''}${chosen ? ' selected' : ''}`.trim() || undefined}>
        <button type="button" className="review-grid-tile" disabled={batch !== null} aria-pressed={chosen}
          title={zh ? `${prompt}\n${zh}` : prompt} aria-label={`${ordinalLabel(tile.job)}${tile.index !== null ? `，图像 ${tile.index + 1}` : ''}${discarded ? '，已弃置' : ''}，${chosen ? '已选择，点击取消选择' : '点击选择'}`}
          onClick={() => selectKeys([tile.key], !chosen)}>
          {tile.index === null ? <span className="review-grid-empty">{tile.job.status === 'failed' ? '生成失败' : tile.job.status === 'succeeded' ? '图片已过期' : '未完成'}</span>
            : preview && preview !== 'error' ? <img src={preview} alt="" loading="lazy" />
              : <span className="review-grid-empty">{preview === 'error' ? '预览不可用' : '加载中…'}</span>}
          {discarded && <span className="review-grid-mark"><Ban size={18} aria-hidden="true" /> 已弃置</span>}
        </button>
        <button className="icon-button review-grid-check" type="button" aria-pressed={chosen} disabled={batch !== null}
          title={chosen ? '取消选择' : '选择'} aria-label={`${chosen ? '取消选择' : '选择'}${ordinalLabel(tile.job)}${tile.index !== null ? `，图像 ${tile.index + 1}` : ''}`}
          onClick={() => selectKeys([tile.key], !chosen)}>{chosen ? <CheckSquare size={16} aria-hidden="true" /> : <Square size={16} aria-hidden="true" />}</button>
        <span className="review-grid-label">{ordinalLabel(tile.job)}{tile.job.image_urls.length > 1 && tile.index !== null ? ` · ${tile.index + 1}` : ''}{override ? ' · 训练词已改' : ''}</span>
        {zh && <span className="review-grid-zh" title={`${prompt}\n${zh}`}>{zh}</span>}
        {tile.index !== null && <button className={`icon-button review-grid-discard${discarded ? ' restore' : ''}`} type="button" disabled={busyKeys.has(tile.key)}
          title={discarded ? '恢复（导出时包含）' : '弃置（导出时跳过，可恢复）'} aria-pressed={discarded}
          aria-label={`${discarded ? '恢复' : '弃置'}${ordinalLabel(tile.job)}${tile.job.image_urls.length > 1 ? `，图像 ${tile.index + 1}` : ''}`}
          onClick={() => void toggle(tile)}>{discarded ? <Undo2 size={14} aria-hidden="true" /> : <Ban size={14} aria-hidden="true" />}</button>}
        {tile.index !== null && <button className="icon-button review-grid-open" type="button" title="查看原图" aria-label={`查看${ordinalLabel(tile.job)}原图`}
          onClick={() => onOpen(tile.offset, tile.index ?? 0)}><Maximize2 size={14} aria-hidden="true" /></button>}
      </li>
    })}</ul>}
    {groups && pages > 1 && <div className="review-grid-pages">
      <button className="secondary" type="button" disabled={current === 0} onClick={() => setPage(current - 1)}>上一页</button>
      <span>第 {current + 1} / {pages} 页 · 共 {visible.length} 张</span>
      <button className="secondary" type="button" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>下一页</button>
    </div>}
  </section>
}
