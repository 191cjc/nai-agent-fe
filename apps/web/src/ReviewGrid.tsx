import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Ban, Dices, Maximize2, RefreshCw, X } from 'lucide-react'
import { ApiFailure, errorText, type GenerationView, type WorkspaceApi } from './api'
import { DATASET_CATEGORIES } from './dataset-prompts'
import { CHARACTER_CATEGORIES } from './character-prompts'

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

/** Remaining replacements: discarded images and failed groups not yet re-run. */
export function pendingReruns(groups: readonly GenerationView[]): GenerationView[] {
  const reruns = new Map<string, number>()
  for (const group of groups) {
    const source = group.parameters.experiment?.rerun_of
    if (source) reruns.set(source, (reruns.get(source) ?? 0) + 1)
  }
  return groups.flatMap(group => {
    const wanted = group.status === 'failed' ? 1 : group.status === 'succeeded' ? group.discarded_images?.length ?? 0 : 0
    return Array.from({ length: Math.max(0, wanted - (reruns.get(group.id) ?? 0)) }, () => group)
  })
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
  const rerunController = useRef<AbortController | null>(null)

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
  const shown = useMemo(() => visible.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE), [visible, current])
  const shownPaths = shown.flatMap(tile => tile.index === null ? [] : [{ key: tile.key, path: tile.job.image_urls[tile.index] }])
  const pathKey = shownPaths.map(item => item.key).join('|')
  const discardedCount = tiles.filter(tile => tile.index !== null && tile.job.discarded_images?.includes(tile.index)).length
  const failedCount = (groups ?? []).filter(group => group.status === 'failed').length
  const pending = useMemo(() => pendingReruns(groups ?? []), [groups])

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

  async function rerunAll() {
    const sources = pending
    if (!sources.length || rerun) return
    if (!window.confirm(`为 ${sources.length} 张已弃置的图片或失败的条目各重跑 1 张（同提示词、新随机种子）？这是 ${sources.length} 次付费生成。已重跑过的不会重复。`)) return
    const controller = new AbortController()
    rerunController.current = controller
    setRerunMessage('')
    setActionError('')
    let done = 0
    setRerun({ done, total: sources.length, waiting: false })
    try {
      for (const source of sources) {
        for (let waits = 0; ; waits += 1) {
          if (controller.signal.aborted) throw new DOMException('Cancelled', 'AbortError')
          try {
            await api.rerunGeneration(source.id, null)
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
        setRerun({ done, total: sources.length, waiting: false })
      }
      setRerunMessage(`已提交 ${done} 张重跑。新图会出现在原条目之后，生成完成后点「刷新」查看。`)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setRerunMessage(`已停止：提交了 ${done} / ${sources.length} 张，剩余的可稍后再点「重跑全部」。`)
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

  return <section className="review-grid" aria-label="网格检查">
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
        : <button className="text-action" type="button" disabled={!pending.length} title="已弃置的图片和失败的条目各重跑 1 张；已重跑过的不会重复"
          onClick={() => void rerunAll()}><Dices size={14} aria-hidden="true" /> 重跑全部待替换（{pending.length}）</button>}
      <button className="icon-button" type="button" title="返回单张查看" aria-label="返回单张查看" onClick={onClose}><X size={18} /></button>
    </div>
    <p className="prompt-hint">点图片标记弃置或恢复（导出时跳过已弃置）；点右上角放大按钮查看原图。每页 {PAGE_SIZE} 张，只加载小尺寸预览，不占用原图缓存。</p>
    {loadError && <p className="alert" role="alert">记录读取失败：{loadError}</p>}
    {actionError && <p className="alert" role="alert">{actionError}</p>}
    {rerunMessage && <p className="subtle" role="status">{rerunMessage}</p>}
    {!groups && !loadError && <p className="subtle" role="status">正在读取训练集记录…</p>}
    {groups && <ul className="review-grid-tiles">{shown.map(tile => {
      const discarded = tile.index !== null && tile.job.discarded_images?.includes(tile.index) === true
      const preview = previews[tile.key]
      const prompt = tile.job.parameters.experiment?.item?.prompt ?? ''
      return <li key={tile.key} className={discarded ? 'discarded' : ''}>
        <button type="button" className="review-grid-tile" disabled={tile.index === null || busyKeys.has(tile.key)} aria-pressed={discarded}
          title={prompt} aria-label={`${ordinalLabel(tile.job)}${tile.index !== null ? `，图像 ${tile.index + 1}` : ''}，${discarded ? '已弃置，点击恢复' : '点击弃置'}`}
          onClick={() => void toggle(tile)}>
          {tile.index === null ? <span className="review-grid-empty">{tile.job.status === 'failed' ? '生成失败' : tile.job.status === 'succeeded' ? '图片已过期' : '未完成'}</span>
            : preview && preview !== 'error' ? <img src={preview} alt="" loading="lazy" />
              : <span className="review-grid-empty">{preview === 'error' ? '预览不可用' : '加载中…'}</span>}
          {discarded && <span className="review-grid-mark"><Ban size={18} aria-hidden="true" /> 已弃置</span>}
        </button>
        <span className="review-grid-label">{ordinalLabel(tile.job)}{tile.job.image_urls.length > 1 && tile.index !== null ? ` · ${tile.index + 1}` : ''}</span>
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
