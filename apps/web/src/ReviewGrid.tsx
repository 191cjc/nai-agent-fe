import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Ban, CheckSquare, Dices, Maximize2, RefreshCw, Square, Undo2, X } from 'lucide-react'
import { ApiFailure, errorText, type GenerationView, type RerunEdits, type WorkspaceApi } from './api'
import { DATASET_CATEGORIES } from './dataset-prompts'
import { CHARACTER_CATEGORIES } from './character-prompts'
import { translatePrompt } from './prompt-zh'
import { datasetItemZh } from './PromptGloss'

/** Tiles per page: bounds preview requests and Blob memory (~60 × 30 KB). */
const PAGE_SIZE = 60
const METADATA_PAGE = 100
const MAX_GROUPS = 3000
const PREVIEW_CONCURRENCY = 4
const BUSY_RETRIES = 3
/** 429 queue_full means "not accepted", so waiting and resubmitting is safe and unpaid. */
const QUEUE_WAIT_MS = 5000
const QUEUE_WAIT_LIMIT = 120

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

export function ReviewGrid({ api, experimentId, onOpen, onClose }: {
  api: WorkspaceApi
  experimentId: string
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
  const [rerun, setRerun] = useState<{ done: number; total: number; waiting: boolean } | null>(null)
  const [rerunMessage, setRerunMessage] = useState('')
  // Selected tiles by key; kept across pages, category and discard filters until submitted or cleared.
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  // Batch editor over the selected tiles: one optional new style, an editable prompt per tile.
  const [batch, setBatch] = useState<{ sources: Tile[]; prompts: string[]; style: string; discardReplaced: boolean } | null>(null)
  const rerunController = useRef<AbortController | null>(null)
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
  // A reload drops selections whose tile no longer exists (e.g. an image expired).
  useEffect(() => {
    if (!groups) return
    const keys = new Set(tiles.map(tile => tile.key))
    setSelected(current => [...current].every(key => keys.has(key)) ? current : new Set([...current].filter(key => keys.has(key))))
  }, [groups, tiles])
  const selectedTiles = useMemo(() => tiles.filter(tile => selected.has(tile.key)), [tiles, selected])
  const hiddenSelected = selectedTiles.length - selectedTiles.filter(tile => visible.includes(tile)).length
  // Quick picks select only what still needs a replacement, so nothing is paid for twice.
  const pendingFailedTiles = useMemo(() => tiles.filter(tile => tile.job.status === 'failed' && !(reruns.get(tile.job.id) ?? 0)), [tiles, reruns])
  const pendingDiscardedTiles = useMemo(() => (groups ?? []).flatMap(group => {
    if (group.status !== 'succeeded') return []
    const marks = [...(group.discarded_images ?? [])].sort((left, right) => left - right)
    const remaining = Math.max(0, marks.length - (reruns.get(group.id) ?? 0))
    return marks.slice(0, remaining).map(index => `${group.id}:${index}`)
  }), [groups, reruns])

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

  useEffect(() => () => rerunController.current?.abort(), [])

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

  function openBatch() {
    if (!selectedTiles.length || rerun) return
    setRerunMessage('')
    setBatch({ sources: selectedTiles, prompts: selectedTiles.map(tile => tile.job.parameters.experiment?.item?.prompt ?? ''), style: '', discardReplaced: true })
  }

  async function rerunAll() {
    if (!batch || rerun) return
    const { sources, prompts, style, discardReplaced } = batch
    if (prompts.some(prompt => !prompt.trim())) { setActionError('训练词不能为空。'); return }
    const repeated = sources.filter(tile => reruns.get(tile.job.id)).length
    if (!window.confirm(`为所选 ${sources.length} 张各重跑 1 张（新随机种子${style.trim() ? '，使用新画风' : '，保持原画风'}）？这是 ${sources.length} 次付费生成。${repeated ? `\n其中 ${repeated} 张所在条目以前已经重跑过。` : ''}`)) return
    const controller = new AbortController()
    rerunController.current = controller
    setRerunMessage('')
    setActionError('')
    setBatch(null)
    let done = 0
    setRerun({ done, total: sources.length, waiting: false })
    try {
      for (const [index, tile] of sources.entries()) {
        const source = tile.job
        const original = source.parameters.experiment?.item?.prompt
        // Replacing a kept image marks it discarded once the re-run is accepted.
        const discardIndex = discardReplaced && tile.index !== null && !source.discarded_images?.includes(tile.index) ? tile.index : null
        const edits: RerunEdits = {
          ...(prompts[index] !== original ? { prompt: prompts[index] } : {}),
          ...(style.trim() ? { style_prompt: style } : {}),
        }
        for (let waits = 0; ; waits += 1) {
          if (controller.signal.aborted) throw new DOMException('Cancelled', 'AbortError')
          try {
            await api.rerunGeneration(source.id, discardIndex, edits)
            break
          } catch (error) {
            // Only a definite "queue full" refusal is safe to resubmit.
            if (error instanceof ApiFailure && error.status === 429 && error.code === 'queue_full' && waits < QUEUE_WAIT_LIMIT) {
              setRerun({ done, total: sources.length, waiting: true })
              await wait(QUEUE_WAIT_MS, controller.signal)
              continue
            }
            throw error
          }
        }
        done += 1
        selectKeys([tile.key], false)
        setRerun({ done, total: sources.length, waiting: false })
      }
      setRerunMessage(`已提交 ${done} 张重跑。新图会出现在原条目之后，生成完成后点「刷新」查看。`)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setRerunMessage(`已停止：提交了 ${done} / ${sources.length} 张，剩余的可稍后再重跑。`)
      } else if (error instanceof ApiFailure) {
        setActionError(`重跑在第 ${done + 1} 张停止（已提交 ${done} 张）：${errorText(error)}`)
      } else {
        // The request may or may not have been accepted: never resubmit blindly.
        setActionError(`第 ${done + 1} 张的提交结果未知（网络中断）。已提交 ${done} 张；请先点「刷新」核对，再决定是否继续。`)
      }
    } finally {
      rerunController.current = null
      setRerun(null)
      setReload(value => value + 1)
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
      <button className="text-action" type="button" disabled={!groups || rerun !== null} onClick={() => setReload(value => value + 1)}><RefreshCw size={14} aria-hidden="true" /> 刷新</button>
      {rerun
        ? <button className="text-action" type="button" onClick={() => rerunController.current?.abort()}><X size={14} aria-hidden="true" /> 停止提交（{rerun.done} / {rerun.total}{rerun.waiting ? '，队列已满，等待中' : ''}）</button>
        : <button className="text-action" type="button" disabled={!selectedTiles.length || batch !== null} title="为所选图片各重跑 1 张；可先改画风和训练词"
          onClick={openBatch}><Dices size={14} aria-hidden="true" /> 重跑所选（{selectedTiles.length}）</button>}
      <button className="icon-button" type="button" title="返回单张查看" aria-label="返回单张查看" onClick={onClose}><X size={18} /></button>
    </div>
    {groups && <div className="review-grid-selection" role="group" aria-label="多选">
      <span role="status">已选 <strong>{selectedTiles.length}</strong> 张{hiddenSelected > 0 ? `（${hiddenSelected} 张不在当前筛选中）` : ''}</span>
      <button className="text-action" type="button" disabled={!pendingFailedTiles.length || batch !== null} title="生成失败且还没补跑过的条目"
        onClick={() => selectKeys(pendingFailedTiles.map(tile => tile.key))}>选择全部失败（{pendingFailedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!pendingDiscardedTiles.length || batch !== null} title="已弃置且还没重跑过的图片"
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
    {batch && <div className="rerun-batch" role="group" aria-label="批量重跑设置">
      <p><strong>重跑所选 {batch.sources.length} 张</strong>：每张 1 次付费生成，新随机种子。改过的训练词会成为新图的 caption。</p>
      <label className="field"><span>新画风（留空则每张保持原来的画风）</span>
        <textarea rows={2} value={batch.style} maxLength={3000} spellCheck={false}
          onChange={event => setBatch({ ...batch, style: event.target.value })} /></label>
      <label className="history-select"><input type="checkbox" checked={batch.discardReplaced}
        onChange={event => setBatch({ ...batch, discardReplaced: event.target.checked })} /> 提交后弃置被替换的原图（只影响还没弃置的成功图片）</label>
      <ol className="rerun-batch-items">{batch.sources.map((tile, index) => <li key={tile.key}>
        <span>{ordinalLabel(tile.job)}{tile.index !== null && tile.job.image_urls.length > 1 ? ` · ${tile.index + 1}` : ''}{tile.job.status === 'failed' ? '（失败）' : tile.index !== null && tile.job.discarded_images?.includes(tile.index) ? '（已弃置）' : ''}{reruns.get(tile.job.id) ? `（已重跑 ${reruns.get(tile.job.id)} 次）` : ''}{tile.job.parameters.experiment?.item?.characters?.length ? '（多人：只改共享场景）' : ''}</span>
        <textarea rows={2} value={batch.prompts[index]} maxLength={1000} spellCheck={false} aria-label={`${ordinalLabel(tile.job)}的训练词`}
          onChange={event => setBatch({ ...batch, prompts: batch.prompts.map((value, at) => at === index ? event.target.value : value) })} />
        <span className="dataset-item-zh">{translatePrompt(batch.prompts[index])}</span>
      </li>)}</ol>
      <div className="rerun-batch-actions">
        <button type="button" onClick={() => void rerunAll()}><Dices size={14} aria-hidden="true" /> 提交 {batch.sources.length} 张</button>
        <button className="secondary" type="button" onClick={() => setBatch(null)}>取消</button>
      </div>
    </div>}
    {!groups && !loadError && <p className="subtle" role="status">正在读取训练集记录…</p>}
    {groups && <ul className="review-grid-tiles">{shown.map(tile => {
      const discarded = tile.index !== null && tile.job.discarded_images?.includes(tile.index) === true
      const preview = previews[tile.key]
      const item = tile.job.parameters.experiment?.item
      const prompt = item?.prompt ?? ''
      const zh = item ? datasetItemZh(item) : ''
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
        <span className="review-grid-label">{ordinalLabel(tile.job)}{tile.job.image_urls.length > 1 && tile.index !== null ? ` · ${tile.index + 1}` : ''}</span>
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
