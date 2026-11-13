import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Ban, CheckSquare, Dices, Maximize2, PencilLine, RefreshCw, Replace, Search, Square, Trash2, Undo2, X } from 'lucide-react'
import { ApiFailure, errorText, type ExperimentRunState, type GenerationView, type ImagePurgeResult, type RerunBatchItem, type WorkspaceApi } from './api'
import { CHARACTER_CATEGORIES } from './character-prompts'
import { translatePrompt } from './prompt-zh'
import { contentCaption } from './dataset-export'
import { datasetItemZh } from './PromptGloss'
import { allImagesPurged, imagePurged, retainedImageIndexes } from './result-images'
import type { DatasetReviewChange } from './saved-results'

/** Tiles per page: bounds preview requests and Blob memory (~60 × 30 KB). */
const PAGE_SIZE = 60
const METADATA_PAGE = 100
// A 4000-item set plus its re-runs; the grid renders PAGE_SIZE at a time.
const MAX_GROUPS = 12000
// Server cap per POST /api/rerun-batches (MAX_RERUN_BATCH).
const MAX_RERUN_BATCH = 3000
const PREVIEW_CONCURRENCY = 4
const BUSY_RETRIES = 3

// Categories of the retired fixed style library, kept so older training sets stay readable.
const LEGACY_STYLE_CATEGORIES: Record<string, string> = {
  portrait: '特写与表情', face: '脸部特写', upper: '半身日常', full: '全身与动作', angle: '视角与透视',
  scene: '人物与场景', light: '光照与时段', multi: '多人互动', fantasy: '异世界奇幻', ornate: '华丽立绘',
  boy: '男孩（年幼）', girl: '女孩（年幼）', nohuman: '无人物',
}

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries([
  ...Object.entries(LEGACY_STYLE_CATEGORIES),
  ...CHARACTER_CATEGORIES.map(category => [category.id, category.label]),
  ['recipe', '随机配方'],
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
  const item = job.parameters.experiment?.item
  if (item?.draws?.length) return 'recipe'
  return (item?.id ?? '').replace(/-\d+$/, '') || 'custom'
}

/** Filter key of a draw: one chip per option, per slot value, and per skip/removal reason. */
interface DrawChip { group: string; groupLabel: string; key: string; label: string }

const DRAW_GROUP_LABELS: Record<string, string> = { '-rule': '规则', '-style': '画风增删', '-meta': '标记' }

function drawChips(job: GenerationView): DrawChip[] {
  const draws = job.parameters.experiment?.item?.draws ?? []
  const chips: DrawChip[] = []
  for (const draw of draws) {
    const groupLabel = DRAW_GROUP_LABELS[draw.partition] ?? draw.label.split('：')[0]
    const optionText = draw.label.includes('：') ? draw.label.slice(draw.label.indexOf('：') + 1) : draw.label
    const key = draw.option === '-skip' || draw.option === '-removed' ? `${draw.option}:${draw.reason ?? ''}` : draw.option
    chips.push({ group: draw.partition, groupLabel, key, label: draw.option === '-removed' ? '被移除' : optionText })
    for (const [slot, value] of Object.entries(draw.values ?? {})) {
      chips.push({ group: `${draw.partition}#${slot}`, groupLabel: `${groupLabel} · ${slot}`, key: value, label: value })
    }
  }
  return chips
}

/** AND across groups, OR within a group; groups with nothing selected do not filter. */
function matchesDraws(chips: readonly DrawChip[], filter: ReadonlyMap<string, ReadonlySet<string>>): boolean {
  for (const [group, keys] of filter) {
    if (keys.size && !chips.some(chip => chip.group === group && keys.has(chip.key))) return false
  }
  return true
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
  // Trim edge commas and collapse the empty tags a removal leaves behind ("a, , b").
  const tidy = (text: string) => text.replace(/,\s*(?=,)/g, '').trim().replace(/^[,\s]+|[,\s]+$/g, '')
  switch (operation.kind) {
    case 'reset': return null
    case 'replace': return tidy(current.split(operation.find).join(operation.replace))
    case 'prefix': return [tidy(operation.text), tidy(current)].filter(Boolean).join(', ')
    case 'suffix': return [tidy(current), tidy(operation.text)].filter(Boolean).join(', ')
  }
}

/**
 * Search terms split on commas (ASCII or full-width); a leading "-" excludes. Matching is a
 * case-insensitive substring test against the training caption and its Chinese gloss.
 */
export function parseSearch(query: string): { include: string[]; exclude: string[] } {
  const include: string[] = []
  const exclude: string[] = []
  for (const raw of query.split(/[,，]/)) {
    const term = raw.trim().toLowerCase()
    if (term.startsWith('-')) { if (term.slice(1).trim()) exclude.push(term.slice(1).trim()) } else if (term) include.push(term)
  }
  return { include, exclude }
}

export function matchesSearch(text: string, search: { include: readonly string[]; exclude: readonly string[] }): boolean {
  return search.include.every(term => text.includes(term)) && !search.exclude.some(term => text.includes(term))
}

/** Training caption of a group plus its Chinese gloss, lower-cased for search. */
function searchText(job: GenerationView): string {
  const override = job.caption_override ?? null
  const item = job.parameters.experiment?.item
  const zh = override ? translatePrompt(override) : item ? datasetItemZh(item) : ''
  return `${contentCaption(job.parameters, override)}\n${zh}`.toLowerCase()
}

type RerunTarget = 'all' | 'scene' | 'people'
type RerunOperation = Exclude<CaptionOperation, { kind: 'reset' }>

/** Batch prompts after one find/replace, prefix or suffix over the chosen prompts. */
export function applyRerunOperation(
  prompts: readonly string[], characters: readonly (readonly string[])[], operation: RerunOperation, target: RerunTarget,
): { prompts: string[]; characters: string[][]; changed: number; blank: number } {
  let changed = 0
  let blank = 0
  const edit = (text: string) => {
    const after = applyCaptionOperation(text, operation) ?? text
    if (!after.trim()) { blank += 1; return text }
    if (after !== text) changed += 1
    return after
  }
  return {
    prompts: prompts.map(text => target === 'people' ? text : edit(text)),
    characters: characters.map(people => people.map(text => target === 'scene' ? text : edit(text))),
    changed, blank,
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

function applyDetailChange(groups: GenerationView[], change: Exclude<DatasetReviewChange, { kind: 'rerun' }>): GenerationView[] {
  return groups.map(group => {
    if (group.id !== change.jobId) return group
    if (change.kind === 'caption') return { ...group, caption_override: change.caption }
    if (imagePurged(group, change.index)) return group
    const marks = new Set(group.discarded_images ?? [])
    if (change.discarded) marks.add(change.index)
    else marks.delete(change.index)
    return { ...group, discarded_images: [...marks].sort((left, right) => left - right) }
  })
}

export function ReviewGrid({ api, experimentId, setName, onQueued, onOpen, onClose, onPurge, subscribeReviewChanges }: {
  api: WorkspaceApi
  experimentId: string
  /** Training-set name, used to label its re-run batches in the queue. */
  setName?: string | null
  /** A re-run batch was accepted: show it in the run queue. */
  onQueued?: (run: ExperimentRunState) => void
  /** Opens the full-size viewer at this group offset and image index. */
  onOpen: (offset: number, image: number) => void
  onClose: () => void
  /** Clears this selection's saved-viewer caches and refreshes its metadata/list. */
  onPurge: () => Promise<ImagePurgeResult>
  /** Selection-owned detail changes, including successful writes after the dialog closes. */
  subscribeReviewChanges: (listener: (change: DatasetReviewChange) => void) => () => void
}) {
  const [groups, setGroups] = useState<GenerationView[] | null>(null)
  const [loadError, setLoadError] = useState('')
  const [reload, setReload] = useState(0)
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [drawFilter, setDrawFilter] = useState<ReadonlyMap<string, ReadonlySet<string>>>(new Map())
  const [drawPanel, setDrawPanel] = useState(false)
  const [hideDiscarded, setHideDiscarded] = useState(true)
  const [metadataLimited, setMetadataLimited] = useState(false)
  const [purging, setPurging] = useState(false)
  const [cleanupMessage, setCleanupMessage] = useState('')
  const [cleanupError, setCleanupError] = useState('')
  const [page, setPage] = useState(0)
  const [previews, setPreviews] = useState<Record<string, string | 'error'>>({})
  const [busyKeys, setBusyKeys] = useState<ReadonlySet<string>>(new Set())
  const [actionError, setActionError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // Not-yet-submitted sources of this set's server-side re-run batches (by source job id).
  const [queued, setQueued] = useState<ReadonlyMap<string, number>>(new Map())
  // Accepted detail re-runs can already have submitted while the grid snapshot is unchanged.
  // Keep a conservative replacement floor until the next explicit metadata refresh.
  const [detailReplacements, setDetailReplacements] = useState<ReadonlyMap<string, number>>(new Map())
  const replacementCountsRef = useRef<ReadonlyMap<string, number>>(new Map())
  // Bulk training-caption editor (training only, never generates).
  const [captionEdit, setCaptionEdit] = useState<{ scope: 'selected' | 'visible' | 'all'; kind: CaptionOperation['kind']; find: string; text: string } | null>(null)
  const [captionBusy, setCaptionBusy] = useState(false)
  const [rerunMessage, setRerunMessage] = useState('')
  // Selected tiles by key; kept across pages, category and discard filters until submitted or cleared.
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  // Batch editor over the selected tiles: one optional new style, an editable prompt per tile.
  // `id` is reused after an unknown outcome so a resubmission cannot queue the batch twice.
  // Multi-person tiles also get one editable prompt per person (`characters[tile][person]`).
  const [batch, setBatch] = useState<{ id: string; sources: Tile[]; prompts: string[]; characters: string[][]; style: string; discardReplaced: boolean } | null>(null)
  // Bulk find/replace, prefix or suffix over the open batch's prompts (applied on click, not live).
  const [batchEdit, setBatchEdit] = useState<{ kind: RerunOperation['kind']; find: string; text: string; target: RerunTarget }>({ kind: 'replace', find: '', text: '', target: 'all' })
  const [batchEditMessage, setBatchEditMessage] = useState('')
  const scrollRef = useRef<HTMLElement | null>(null)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  // Metadata only (no image bytes): bounded pages in server order.
  useEffect(() => {
    const controller = new AbortController()
    const pendingChanges: Exclude<DatasetReviewChange, { kind: 'rerun' }>[] = []
    let metadataPending = true
    let queueSnapshot: ExperimentRunState[] = []
    const acceptedRuns = new Map<string, ExperimentRunState>()
    const updateQueued = () => {
      const runs = new Map(queueSnapshot.map(run => [run.id, run]))
      acceptedRuns.forEach((run, id) => {
        const snapshot = runs.get(id)
        if (!snapshot || snapshot.updated_at < run.updated_at
          || (snapshot.updated_at === run.updated_at && Number(snapshot.next_ordinal) < Number(run.next_ordinal))) runs.set(id, run)
      })
      setQueued(queuedRerunSources([...runs.values()], experimentId))
    }
    const unsubscribe = subscribeReviewChanges(change => {
      if (controller.signal.aborted) return
      if (change.kind === 'rerun') {
        if (!acceptedRuns.has(change.run.id)) {
          const sources = new Map<string, number>()
          for (const item of change.run.rerun_items ?? [{ job_id: change.jobId }]) sources.set(item.job_id, (sources.get(item.job_id) ?? 0) + 1)
          const known = queuedRerunSources(queueSnapshot.filter(run => run.id === change.run.id), experimentId)
          setDetailReplacements(currentCounts => {
            const next = new Map(currentCounts)
            sources.forEach((count, id) => next.set(id,
              Math.max(0, Math.max(next.get(id) ?? 0, replacementCountsRef.current.get(id) ?? 0) - (known.get(id) ?? 0)) + count))
            return next
          })
        }
        acceptedRuns.set(change.run.id, change.run)
        updateQueued()
      } else {
        // A read started before this write must not overwrite its accepted result.
        if (metadataPending) pendingChanges.push(change)
        setGroups(currentGroups => currentGroups ? applyDetailChange(currentGroups, change) : null)
      }
    })
    setGroups(null)
    setDetailReplacements(new Map())
    setLoadError('')
    setMetadataLimited(false)
    void (async () => {
      const loaded: GenerationView[] = []
      let offset: number | null = 0
      while (offset !== null && loaded.length < MAX_GROUPS) {
        const result = await api.experiment(experimentId, offset, METADATA_PAGE, controller.signal)
        loaded.push(...result.items)
        offset = result.next_offset
      }
      if (!controller.signal.aborted) {
        setGroups(pendingChanges.reduce(applyDetailChange, loaded))
        metadataPending = false
        pendingChanges.length = 0
        setMetadataLimited(offset !== null)
      }
    })().catch(error => {
      if (!controller.signal.aborted) {
        metadataPending = false
        pendingChanges.length = 0
        setLoadError(errorText(error))
      }
    })
    // Best effort: without the queue, quick picks just cannot exclude batched sources.
    void api.queuedExperimentRuns(controller.signal)
      .then(runs => { if (!controller.signal.aborted) { queueSnapshot = runs; updateQueued() } })
      .catch(() => undefined)
    return () => { controller.abort(); unsubscribe() }
  }, [api, experimentId, reload, subscribeReviewChanges])

  const tiles = useMemo<Tile[]>(() => (groups ?? []).flatMap((job, offset): Tile[] => {
    const base = { offset, job, category: categoryOf(job) }
    if (allImagesPurged(job)) return []
    if (job.status !== 'succeeded' || !job.image_urls.length) return [{ ...base, key: `${job.id}:x`, index: null }]
    return retainedImageIndexes(job).map(index => ({ ...base, key: `${job.id}:${index}`, index }))
  }), [groups])
  const categories = useMemo(() => [...new Set((groups ?? []).map(categoryOf))], [groups])
  // Per group, computed once per load or caption edit (not per keystroke).
  const searchIndex = useMemo(() => new Map((groups ?? []).map(job => [job.id, searchText(job)])), [groups])
  const search = useMemo(() => parseSearch(query), [query])
  const chipIndex = useMemo(() => new Map((groups ?? []).map(job => [job.id, drawChips(job)])), [groups])
  const drawFiltering = [...drawFilter.values()].some(keys => keys.size > 0)
  const searching = search.include.length > 0 || search.exclude.length > 0 || drawFiltering
  const visible = useMemo(() => tiles.filter(tile => (category === 'all' || tile.category === category)
    && !(hideDiscarded && tile.index !== null && tile.job.discarded_images?.includes(tile.index))
    && ((!search.include.length && !search.exclude.length) || matchesSearch(searchIndex.get(tile.job.id) ?? '', search))
    && (!drawFiltering || matchesDraws(chipIndex.get(tile.job.id) ?? [], drawFilter))), [tiles, category, hideDiscarded, searchIndex, search, drawFiltering, chipIndex, drawFilter])
  // Draw groups present in this set with per-chip image counts (before draw filtering).
  const drawGroups = useMemo(() => {
    const result = new Map<string, { label: string; chips: Map<string, { label: string; count: number }> }>()
    for (const tile of tiles) {
      if (hideDiscarded && tile.index !== null && tile.job.discarded_images?.includes(tile.index)) continue
      for (const chip of chipIndex.get(tile.job.id) ?? []) {
        const group = result.get(chip.group) ?? { label: chip.groupLabel, chips: new Map() }
        const entry = group.chips.get(chip.key) ?? { label: chip.label, count: 0 }
        entry.count += 1
        group.chips.set(chip.key, entry)
        result.set(chip.group, group)
      }
    }
    return result
  }, [tiles, chipIndex, hideDiscarded])
  function toggleDraw(group: string, key: string) {
    setDrawFilter(current => {
      const next = new Map(current)
      const keys = new Set(next.get(group) ?? [])
      if (keys.has(key)) keys.delete(key)
      else keys.add(key)
      next.set(group, keys)
      return next
    })
    setPage(0)
  }
  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE))
  const current = Math.min(page, pages - 1)
  useEffect(() => { scrollRef.current?.scrollTo({ top: 0 }) }, [current])
  const shown = useMemo(() => visible.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE), [visible, current])
  const shownPaths = shown.flatMap(tile => tile.index === null ? [] : [{ key: tile.key, path: tile.job.image_urls[tile.index] }])
  const pathKey = shownPaths.map(item => item.key).join('|')
  const discardedCount = tiles.filter(tile => tile.index !== null && tile.job.discarded_images?.includes(tile.index)).length
  const cleanupCount = (groups ?? []).reduce((count, group) => {
    if (group.status !== 'succeeded') return count
    const targets = new Set((group.discarded_images ?? []).filter(index => !imagePurged(group, index)))
    group.purge_pending_images?.forEach(index => targets.add(index))
    return count + targets.size
  }, 0)
  const cleanupPendingCount = (groups ?? []).reduce((count, group) => count + (group.purge_pending_images?.length ?? 0), 0)
  const failedCount = (groups ?? []).filter(group => group.status === 'failed').length
  const reruns = useMemo(() => rerunCounts(groups ?? []), [groups])
  // Made plus still queued on the server: what quick picks treat as already replaced.
  const replaced = useMemo(() => {
    const counts = new Map(reruns)
    queued.forEach((count, id) => counts.set(id, (counts.get(id) ?? 0) + count))
    detailReplacements.forEach((count, id) => counts.set(id, Math.max(counts.get(id) ?? 0, count)))
    return counts
  }, [reruns, queued, detailReplacements])
  useEffect(() => { replacementCountsRef.current = replaced }, [replaced])
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
    const marks = (group.discarded_images ?? []).filter(index => !imagePurged(group, index)).sort((left, right) => left - right)
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
    if (tile.index === null || busyKeys.has(tile.key) || purging || imagePurged(tile.job, tile.index)) return
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
  }, [api, busyKeys, purging])

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
    if (!selectedTiles.length || submitting || purging) return
    const id = newBatchId()
    if (!id) return
    setRerunMessage('')
    setBatchEditMessage('')
    setBatch({
      id, sources: selectedTiles, style: '', discardReplaced: true,
      prompts: selectedTiles.map(tile => tile.job.parameters.experiment?.item?.prompt ?? ''),
      characters: selectedTiles.map(tile => (tile.job.parameters.experiment?.item?.characters ?? []).map(person => person.prompt)),
    })
  }

  function applyBatchEdit() {
    if (!batch) return
    const operation: RerunOperation | null = batchEdit.kind === 'replace'
      ? (batchEdit.find ? { kind: 'replace', find: batchEdit.find, replace: batchEdit.text } : null)
      : (batchEdit.text.trim() ? { kind: batchEdit.kind, text: batchEdit.text } : null)
    if (!operation) return
    const result = applyRerunOperation(batch.prompts, batch.characters, operation, batchEdit.target)
    setBatch({ ...batch, prompts: result.prompts, characters: result.characters })
    setBatchEditMessage(`已修改 ${result.changed} 处训练词${result.blank ? `；${result.blank} 处改完会变空，已跳过` : ''}。提交前可逐条检查。`)
  }

  async function rerunAll() {
    if (!batch || submitting || purging) return
    const { id, sources, prompts, characters, style, discardReplaced } = batch
    if (prompts.some(prompt => !prompt.trim()) || characters.some(people => people.some(prompt => !prompt.trim()))) { setActionError('训练词不能为空（包括每个人物）。'); return }
    if (sources.length > MAX_RERUN_BATCH) { setActionError(`一次最多重跑 ${MAX_RERUN_BATCH} 张，请分批选择。`); return }
    const repeated = sources.filter(tile => replaced.get(tile.job.id)).length
    if (!window.confirm(`为所选 ${sources.length} 张各重跑 1 张（新随机种子${style.trim() ? '，使用新画风' : '，保持原画风'}）？这是 ${sources.length} 次付费生成。\n会作为一个任务加入服务器队列，在后台按顺序生成，提交后可以关闭页面。${repeated ? `\n其中 ${repeated} 张所在条目以前已经重跑过或正在排队重跑。` : ''}`)) return
    const items: RerunBatchItem[] = sources.map((tile, index) => {
      const source = tile.job
      // Replacing a kept image marks it discarded when the server submits its re-run.
      const discard = discardReplaced && tile.index !== null && !source.discarded_images?.includes(tile.index)
      const people = (source.parameters.experiment?.item?.characters ?? []).map(person => person.prompt)
      const editedPeople = people.length > 0 && characters[index].some((text, at) => text !== people[at])
      return {
        job_id: source.id,
        ...(discard && tile.index !== null ? { discard_index: tile.index } : {}),
        ...(prompts[index] !== source.parameters.experiment?.item?.prompt ? { prompt: prompts[index] } : {}),
        ...(editedPeople ? { characters: characters[index] } : {}),
        ...(style.trim() ? { style_prompt: style } : {}),
      }
    })
    const name = `${(setName || '训练集').slice(0, 72)} · 重跑`
    setSubmitting(true)
    setRerunMessage('')
    setActionError('')
    try {
      const run = await api.createRerunBatch({ id, experiment_id: experimentId, items, name })
      if (!mounted.current) return
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
    if (!captionPlan || !captionPlan.changes.length || captionBusy || purging) return
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

  async function cleanupDiscarded() {
    if (!groups || purging || submitting || captionBusy || busyKeys.size || batch || captionEdit || (!cleanupCount && !metadataLimited)) return
    const name = setName ? `「${setName}」` : '当前未命名训练集'
    const count = metadataLimited ? `当前已读取记录中有 ${cleanupCount} 张待清理，完整数量可能更多` : `共 ${cleanupCount} 张待清理`
    if (!window.confirm(`确定永久清理${name}中全部已弃置图片？\n\n${count}。范围包含本训练集所有分页和重跑图片，不受当前分类、搜索或选择影响。\n图片会彻底删除，无法恢复；未弃置图片、参考图和生成参数记录会保留。`)) return
    setPurging(true)
    setCleanupMessage('')
    setCleanupError('')
    setActionError('')
    // Immediately release this page's previews while server cleanup is in flight.
    setGroups(null)
    try {
      const result = await onPurge()
      if (!mounted.current) return
      setCleanupMessage(`已永久删除 ${result.deleted_images} 张图片${result.missing_images ? `，${result.missing_images} 张已过期或不存在` : ''}。`)
      if (result.failed_images) setCleanupError(`${result.failed_images} 张尚未完成文件清理，已禁止查看或恢复；可再次点击「清理已弃置图片」重试。`)
    } catch (error) {
      if (!mounted.current) return
      setCleanupError(`清理结果暂无法确认：${errorText(error)} 刷新记录后可再次清理，重复清理不会影响未弃置图片。`)
    } finally {
      if (mounted.current) {
        setPurging(false)
        setReload(value => value + 1)
      }
    }
  }

  return <section ref={scrollRef} className="review-grid" tabIndex={-1} aria-label="网格检查" aria-busy={purging}>
    <div className="review-grid-toolbar">
      <label className="field review-grid-filter"><span>分类</span>
        <select value={category} onChange={event => { setCategory(event.target.value); setPage(0) }}>
          <option value="all">全部（{tiles.length}）</option>
          {categories.map(id => <option key={id} value={id}>{CATEGORY_LABELS[id] ?? id}（{tiles.filter(tile => tile.category === id).length}）</option>)}
        </select></label>
      <label className="field review-grid-search"><span>搜索训练词</span>
        <span className="review-grid-search-input"><Search size={14} aria-hidden="true" />
          <input type="search" value={query} maxLength={500} spellCheck={false} placeholder="如 red hair, -hat"
            title="在训练词（含中文释义）里搜索，不区分大小写；逗号分隔多个词时须全部包含，词前加 - 表示排除"
            onChange={event => { setQuery(event.target.value); setPage(0) }} /></span></label>
      {drawGroups.size > 0 && <button className="text-action" type="button" aria-expanded={drawPanel} onClick={() => setDrawPanel(value => !value)}>
        按随机词筛选{drawFiltering ? `（${[...drawFilter.values()].reduce((sum, keys) => sum + keys.size, 0)}）` : ''}</button>}
      <label className="history-select"><input type="checkbox" checked={hideDiscarded} onChange={event => { setHideDiscarded(event.target.checked); setPage(0) }} /> 隐藏已弃置</label>
      <span className="subtle" role="status">{searching ? `搜索到 ${visible.length} 张 · ` : ''}已弃置 {discardedCount} 张 · 失败 {failedCount} 条</span>
      {cleanupPendingCount > 0 && <span className="subtle" role="status">待重试清理 {cleanupPendingCount} 张</span>}
      {queuedCount > 0 && <span className="subtle" role="status">排队中的重跑 {queuedCount} 张</span>}
      <button className="text-action" type="button" disabled={(!groups && !loadError) || submitting || purging} onClick={() => setReload(value => value + 1)}><RefreshCw size={14} aria-hidden="true" /> 刷新</button>
      <button className="text-action" type="button" disabled={!selectedTiles.length || batch !== null || submitting} title="为所选图片各重跑 1 张；可先改画风和训练词"
        onClick={openBatch}><Dices size={14} aria-hidden="true" /> 重跑所选（{selectedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!groups || captionEdit !== null || captionBusy} title="对已选、当前筛选或全部条目的训练词做替换、加前缀、加后缀；只影响导出"
        onClick={() => setCaptionEdit({ scope: selectedTiles.length ? 'selected' : 'all', kind: 'replace', find: '', text: '' })}><PencilLine size={14} aria-hidden="true" /> 批量改训练词</button>
      <button className="text-action danger-text" type="button" disabled={!groups || purging || submitting || captionBusy || busyKeys.size > 0 || batch !== null || captionEdit !== null || (!cleanupCount && !metadataLimited)}
        title="永久删除当前训练集全部已弃置图片，包含所有分页和重跑图片，不受筛选与选择影响"
        onClick={() => void cleanupDiscarded()}><Trash2 size={14} aria-hidden="true" /> {purging ? '正在清理…' : '清理已弃置图片'}{cleanupCount ? `（${metadataLimited ? '至少 ' : ''}${cleanupCount}）` : ''}</button>
      <button className="icon-button" type="button" disabled={purging} title="返回单张查看" aria-label="返回单张查看" onClick={onClose}><X size={18} /></button>
    </div>
    {drawPanel && drawGroups.size > 0 && <div className="review-draw-filter" role="group" aria-label="按随机词筛选">
      <p className="prompt-hint">不同分区之间须同时满足，同一分区内任选其一；数字为图片张数。只对随机配方生成的条目有效。</p>
      {[...drawGroups.entries()].map(([group, entry]) => <div key={group} className="review-draw-group">
        <strong>{entry.label}</strong>
        {[...entry.chips.entries()].sort((a, b) => b[1].count - a[1].count).map(([key, chip]) => {
          const active = drawFilter.get(group)?.has(key) ?? false
          return <button key={key} type="button" className={`recipe-chip ${active ? 'only' : ''}`} aria-pressed={active} onClick={() => toggleDraw(group, key)}>{chip.label} {chip.count}</button>
        })}
      </div>)}
      <button className="text-action" type="button" disabled={!drawFiltering} onClick={() => { setDrawFilter(new Map()); setPage(0) }}>清除随机词筛选</button>
    </div>}
    {groups && <div className="review-grid-selection" role="group" aria-label="多选">
      <span role="status">已选 <strong>{selectedTiles.length}</strong> 张{hiddenSelected > 0 ? `（${hiddenSelected} 张不在当前筛选中）` : ''}</span>
      <button className="text-action" type="button" disabled={!pendingFailedTiles.length || batch !== null} title="生成失败、还没补跑过也不在重跑队列中的条目"
        onClick={() => selectKeys(pendingFailedTiles.map(tile => tile.key))}>选择全部失败（{pendingFailedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!pendingDiscardedTiles.length || batch !== null} title="已弃置、还没重跑过也不在重跑队列中的图片"
        onClick={() => selectKeys(pendingDiscardedTiles)}>选择全部已弃置（{pendingDiscardedTiles.length}）</button>
      <button className="text-action" type="button" disabled={!shown.length || batch !== null} onClick={() => selectKeys(shown.map(tile => tile.key))}>选择本页</button>
      <button className="text-action" type="button" disabled={!visible.length || batch !== null} title="当前分类、搜索和筛选下的全部图片（所有页）"
        onClick={() => selectKeys(visible.map(tile => tile.key))}>{searching ? '选择搜索结果' : '选择筛选结果'}（{visible.length}）</button>
      {searching && <button className="text-action" type="button" disabled={!visible.some(tile => selected.has(tile.key)) || batch !== null}
        title="只取消当前搜索结果中的已选图片" onClick={() => selectKeys(visible.map(tile => tile.key), false)}>取消选择搜索结果</button>}
      <button className="text-action" type="button" disabled={!selected.size || batch !== null} onClick={() => setSelected(new Set())}>清空选择</button>
    </div>}
    <p className="prompt-hint">点图片选择或取消选择，点右上角 ⊘ 按钮弃置或恢复（导出时跳过已弃置）；可在「搜索训练词」里查找后「选择搜索结果」批量选中；多选后「重跑所选」，翻页、切换分类和搜索不会丢失已选；点右上角放大按钮查看原图。每页 {PAGE_SIZE} 张，只加载小尺寸预览，不占用原图缓存。</p>
    {loadError && <p className="alert" role="alert">记录读取失败：{loadError}</p>}
    {actionError && <p className="alert" role="alert">{actionError}</p>}
    {purging && <p className="subtle" role="status">正在永久清理当前训练集的已弃置图片…</p>}
    {cleanupMessage && <p className="subtle" role="status">{cleanupMessage}</p>}
    {cleanupError && <p className="alert" role="alert">{cleanupError}</p>}
    {metadataLimited && <p className="prompt-hint">本次只展示前 {MAX_GROUPS} 条记录；清理仍覆盖当前训练集全部已弃置图片。</p>}
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
      <div className="rerun-batch-replace" role="group" aria-label="批量替换训练词">
        <div className="caption-bulk-row" role="radiogroup" aria-label="替换操作">
          <span>批量修改下面的训练词</span>
          {([['replace', '文本替换'], ['prefix', '加前缀'], ['suffix', '加后缀']] as const).map(([value, label]) =>
            <label key={value} className="history-select"><input type="radio" name="rerun-edit-kind" checked={batchEdit.kind === value} disabled={submitting}
              onChange={() => setBatchEdit({ ...batchEdit, kind: value })} /> {label}</label>)}
        </div>
        {batch.characters.some(people => people.length > 0) && <div className="caption-bulk-row" role="radiogroup" aria-label="替换范围">
          <span>范围</span>
          {([['all', '场景和人物'], ['scene', '只改场景'], ['people', '只改人物']] as const).map(([value, label]) =>
            <label key={value} className="history-select"><input type="radio" name="rerun-edit-target" checked={batchEdit.target === value} disabled={submitting}
              onChange={() => setBatchEdit({ ...batchEdit, target: value })} /> {label}</label>)}
        </div>}
        <div className="caption-bulk-fields">
          {batchEdit.kind === 'replace' && <label className="field"><span>查找（区分大小写，替换全部出现处）</span>
            <input type="text" value={batchEdit.find} maxLength={1000} spellCheck={false} disabled={submitting}
              onChange={event => setBatchEdit({ ...batchEdit, find: event.target.value })} /></label>}
          <label className="field"><span>{batchEdit.kind === 'replace' ? '替换为（留空即删除）' : batchEdit.kind === 'prefix' ? '加在最前面' : '加在最后面'}</span>
            <input type="text" value={batchEdit.text} maxLength={1000} spellCheck={false} disabled={submitting}
              onChange={event => setBatchEdit({ ...batchEdit, text: event.target.value })} /></label>
          <button className="secondary" type="button" disabled={submitting || (batchEdit.kind === 'replace' ? !batchEdit.find : !batchEdit.text.trim())}
            onClick={applyBatchEdit}><Replace size={14} aria-hidden="true" /> 应用到 {batch.sources.length} 张</button>
        </div>
        {batchEditMessage && <p className="subtle" role="status">{batchEditMessage}</p>}
      </div>
      <ol className="rerun-batch-items">{batch.sources.map((tile, index) => {
        const people = batch.characters[index]
        return <li key={tile.key}>
          <span>{ordinalLabel(tile.job)}{tile.index !== null && tile.job.image_urls.length > 1 ? ` · ${tile.index + 1}` : ''}{tile.job.status === 'failed' ? '（失败）' : tile.index !== null && tile.job.discarded_images?.includes(tile.index) ? '（已弃置）' : ''}{reruns.get(tile.job.id) ? `（已重跑 ${reruns.get(tile.job.id)} 次）` : ''}{queued.get(tile.job.id) ? `（重跑排队中 ${queued.get(tile.job.id)} 张）` : ''}{people.length ? `（多人：${people.length} 人）` : ''}</span>
          {people.length > 0 && <span className="subtle">场景</span>}
          <textarea rows={2} value={batch.prompts[index]} maxLength={1000} spellCheck={false} aria-label={`${ordinalLabel(tile.job)}的${people.length ? '场景' : ''}训练词`}
            onChange={event => setBatch({ ...batch, prompts: batch.prompts.map((value, at) => at === index ? event.target.value : value) })} />
          <span className="dataset-item-zh">{translatePrompt(batch.prompts[index])}</span>
          {people.map((text, person) => <div key={person} className="rerun-batch-person">
            <span className="subtle">人物 {person + 1}（位置不变）</span>
            <textarea rows={2} value={text} maxLength={1000} spellCheck={false} aria-label={`${ordinalLabel(tile.job)}的人物 ${person + 1} 训练词`}
              onChange={event => setBatch({ ...batch, characters: batch.characters.map((row, at) => at === index ? row.map((value, which) => which === person ? event.target.value : value) : row) })} />
            <span className="dataset-item-zh">{translatePrompt(text)}</span>
          </div>)}
        </li>
      })}</ol>
      <div className="rerun-batch-actions">
        <button type="button" disabled={submitting} onClick={() => void rerunAll()}><Dices size={14} aria-hidden="true" /> {submitting ? '正在加入队列...' : `加入队列（${batch.sources.length} 张）`}</button>
        <button className="secondary" type="button" disabled={submitting} onClick={() => setBatch(null)}>取消</button>
      </div>
    </div>}
    {!groups && !loadError && <p className="subtle" role="status">正在读取训练集记录…</p>}
    {groups && !visible.length && <p className="subtle" role="status">当前筛选下没有可查看的图片。</p>}
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
