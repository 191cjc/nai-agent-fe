import { makeAutoObservable, runInAction } from 'mobx'
import { ApiFailure, errorText, type ExperimentSummary, type GenerationView, WorkspaceApi } from './api'

type SavedSelection = { kind: 'generation' | 'experiment'; id: string }
type PreloadStatus = 'idle' | 'reading' | 'loading' | 'completed' | 'cancelled' | 'capacity' | 'error'

interface SavedImage {
  url: string
  filename: string
  index: number
}

interface CachedImage {
  url: string
  size: number
  expiresAt: number
}

interface TransientImage {
  path: string
  url: string
  size: number
  expiresAt: number | null
}

const IMAGE_CACHE_LIMIT = 32
const IMAGE_CACHE_BYTES = 64 * 1024 * 1024
const PRELOAD_CACHE_LIMIT = 256
const PRELOAD_CACHE_BYTES = 256 * 1024 * 1024
const PRELOAD_PAGE_SIZE = 20

/** Read-only archive access, independent of the paid generation owner. */
export class SavedResultsStore {
  experiments: ExperimentSummary[] = []
  listOffset = 0
  nextListOffset: number | null = null
  listLoaded = false
  listLoading = false
  listError = ''
  selection: SavedSelection | null = null
  summary: ExperimentSummary | null = null
  job: GenerationView | null = null
  groupOffset = 0
  nextGroupOffset: number | null = null
  imageIndex = 0
  /** Review mode: left/right navigation skips images marked as discarded. */
  hideDiscarded = false
  discardBusy = false
  discardError = ''
  rerunBusy = false
  rerunError = ''
  rerunMessage = ''
  image: SavedImage | null = null
  loading = false
  imageLoading = false
  error = ''
  imageError = ''
  preloadStatus: PreloadStatus = 'idle'
  preloadGroupLimit: number | null = null
  preloadProcessedGroups = 0
  preloadProcessedImages = 0
  preloadSkippedGroups = 0
  preloadFailedImages = 0
  preloadError = ''
  preloadImageError = ''
  private listEpoch = 0
  private viewerEpoch = 0
  private preloadEpoch = 0
  private requestedImage: number | 'last' = 0
  private listController: AbortController | null = null
  private viewerController: AbortController | null = null
  private preloadController: AbortController | null = null
  private preloadCacheEnabled = false
  private readonly imageCache = new Map<string, CachedImage>()
  private imageCacheBytes = 0
  private transientImage: TransientImage | null = null

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  async loadExperiments(offset = this.listOffset): Promise<void> {
    const epoch = ++this.listEpoch
    this.listController?.abort()
    const controller = new AbortController()
    this.listController = controller
    this.listLoading = true
    this.listError = ''
    try {
      const page = await this.api.experiments(offset, 20, controller.signal)
      if (epoch !== this.listEpoch) return
      runInAction(() => {
        this.experiments = page.items
        this.listOffset = offset
        this.nextListOffset = page.next_offset
        this.listLoaded = true
      })
    } catch (error) {
      if (epoch === this.listEpoch) runInAction(() => { this.listError = errorText(error) })
    } finally {
      if (epoch === this.listEpoch) runInAction(() => { this.listLoading = false })
    }
  }

  async openGeneration(id: string): Promise<void> {
    this.close()
    this.selection = { kind: 'generation', id }
    await this.loadGroup(0)
  }

  async openExperiment(id: string): Promise<void> {
    this.close()
    this.selection = { kind: 'experiment', id }
    await this.loadGroup(0)
  }

  get imageSlots(): number {
    return this.job?.status === 'succeeded' ? Math.max(1, this.job.image_urls.length) : 1
  }

  get canPrevious(): boolean {
    return !this.loading && this.job !== null && (this.imageIndex > 0 || (this.selection?.kind === 'experiment' && this.groupOffset > 0))
  }

  get canNext(): boolean {
    return !this.loading && this.job !== null && (this.imageIndex + 1 < this.imageSlots
      || (this.selection?.kind === 'experiment' && this.nextGroupOffset !== null))
  }

  get preloading(): boolean {
    return this.preloadStatus === 'reading' || this.preloadStatus === 'loading'
  }

  get cachedImageCount(): number {
    return this.imageCache.size
  }

  get cachedImageBytes(): number {
    return this.imageCacheBytes
  }

  private get cacheLimit(): number {
    return this.preloadCacheEnabled ? PRELOAD_CACHE_LIMIT : IMAGE_CACHE_LIMIT
  }

  private get cacheByteLimit(): number {
    return this.preloadCacheEnabled ? PRELOAD_CACHE_BYTES : IMAGE_CACHE_BYTES
  }

  /** An explicit, read-only pass bounded to the groups recorded at its start. */
  async preloadImages(): Promise<void> {
    const selection = this.selection
    if (selection?.kind !== 'experiment' || this.preloading) return
    const epoch = ++this.preloadEpoch
    const controller = new AbortController()
    this.preloadController = controller
    this.preloadCacheEnabled = true
    this.pruneExpiredImages()
    this.preloadStatus = 'reading'
    this.preloadGroupLimit = null
    this.preloadProcessedGroups = 0
    this.preloadProcessedImages = 0
    this.preloadSkippedGroups = 0
    this.preloadFailedImages = 0
    this.preloadError = ''
    this.preloadImageError = ''
    try {
      let groupLimit: number | null = null
      for (let offset = 0; groupLimit === null || offset < groupLimit; offset += PRELOAD_PAGE_SIZE) {
        runInAction(() => { this.preloadStatus = 'reading' })
        const page = await this.api.experiment(selection.id, offset, PRELOAD_PAGE_SIZE, controller.signal)
        if (!this.isCurrentPreload(epoch, selection.id, controller.signal)) return
        if (page.summary.id !== selection.id || !Number.isSafeInteger(page.summary.group_count) || page.summary.group_count < 0
          || page.items.length > PRELOAD_PAGE_SIZE || page.items.some(job => job.parameters.experiment?.id !== selection.id)) {
          throw new ApiFailure(0, 'invalid_response', '实验记录不匹配，请重新加载全部图片。')
        }
        if (groupLimit === null) {
          groupLimit = page.summary.group_count
          runInAction(() => { this.preloadGroupLimit = groupLimit })
        }
        const expectedGroups = Math.min(PRELOAD_PAGE_SIZE, groupLimit - offset)
        for (const job of page.items.slice(0, expectedGroups)) {
          if (!this.isCurrentPreload(epoch, selection.id, controller.signal)) return
          const expiresAt = job.result_expires_at
          if (job.status !== 'succeeded' || job.image_urls.length === 0 || expiresAt === null
            || !Number.isFinite(expiresAt) || expiresAt <= Date.now() / 1000) {
            runInAction(() => {
              this.preloadSkippedGroups += 1
              this.preloadProcessedGroups += 1
            })
            continue
          }
          for (const path of job.image_urls) {
            if (!this.isCurrentPreload(epoch, selection.id, controller.signal)) return
            runInAction(() => { this.preloadStatus = 'loading' })
            try {
              if (!this.cachedImage(path, expiresAt)) {
                // Do not evict earlier preloads just to make this pass continue.
                if (this.imageCache.size >= this.cacheLimit) {
                  runInAction(() => { this.preloadStatus = 'capacity' })
                  return
                }
                const blob = await this.api.image(path, controller.signal)
                if (!this.isCurrentPreload(epoch, selection.id, controller.signal)) return
                // Foreground navigation may have cached this same path during the read.
                if (!this.cachedImage(path, expiresAt) && !this.retainPreloadedImage(path, blob, expiresAt)) {
                  runInAction(() => { this.preloadStatus = 'capacity' })
                  return
                }
              }
            } catch (error) {
              if (!this.isCurrentPreload(epoch, selection.id, controller.signal)) return
              runInAction(() => {
                this.preloadFailedImages += 1
                this.preloadImageError = errorText(error)
              })
            }
            runInAction(() => { this.preloadProcessedImages += 1 })
          }
          runInAction(() => { this.preloadProcessedGroups += 1 })
        }
        if (page.items.length < expectedGroups) {
          throw new ApiFailure(0, 'invalid_response', '实验记录已变化，部分记录尚未检查，请重新加载全部图片。')
        }
      }
      runInAction(() => { this.preloadStatus = 'completed' })
    } catch (error) {
      if (this.isCurrentPreload(epoch, selection.id, controller.signal)) runInAction(() => {
        this.preloadStatus = 'error'
        this.preloadError = errorText(error)
      })
    } finally {
      if (this.isCurrentPreload(epoch, selection.id, controller.signal)) runInAction(() => {
        this.pruneExpiredImages()
        this.preloadController = null
      })
    }
  }

  cancelPreload(): void {
    if (!this.preloading) return
    this.preloadEpoch += 1
    this.preloadController?.abort()
    this.preloadController = null
    this.pruneExpiredImages()
    this.preloadStatus = 'cancelled'
  }

  private isCurrentPreload(epoch: number, id: string, signal: AbortSignal): boolean {
    return epoch === this.preloadEpoch && !signal.aborted && this.selection?.kind === 'experiment' && this.selection.id === id
  }

  get currentDiscarded(): boolean {
    return this.job?.discarded_images?.includes(this.imageIndex) === true
  }

  setHideDiscarded(value: boolean): void {
    this.hideDiscarded = value
  }

  /** Marks or restores the shown image on the server; the file itself is kept. */
  async toggleDiscard(): Promise<void> {
    const job = this.job
    const index = this.imageIndex
    if (!job || job.status !== 'succeeded' || index >= job.image_urls.length || this.discardBusy) return
    const discarded = !this.currentDiscarded
    const epoch = this.viewerEpoch
    this.discardBusy = true
    this.discardError = ''
    try {
      await this.api.setImageDiscarded(job.id, index, discarded)
      runInAction(() => {
        if (epoch !== this.viewerEpoch || this.job?.id !== job.id) return
        const marks = new Set(this.job.discarded_images ?? [])
        if (discarded) marks.add(index)
        else marks.delete(index)
        this.job = { ...this.job, discarded_images: [...marks].sort((left, right) => left - right) }
      })
    } catch (error) {
      runInAction(() => { this.discardError = errorText(error) })
    } finally {
      runInAction(() => { this.discardBusy = false })
    }
  }

  /** Training-set groups only; failed groups and expired images can be re-run too. */
  get canRerun(): boolean {
    const job = this.job
    return this.selection?.kind === 'experiment' && job?.parameters.experiment?.kind === 'dataset'
      && (job.status === 'succeeded' || job.status === 'failed')
  }

  /**
   * One paid generation: same frozen prompt/settings/references, one sample, new random
   * seed. The shown image is marked discarded so the export keeps only the replacement.
   */
  async rerunCurrent(): Promise<void> {
    const job = this.job
    if (!job || !this.canRerun || this.rerunBusy) return
    const index = job.status === 'succeeded' && this.imageIndex < job.image_urls.length
      && !this.currentDiscarded ? this.imageIndex : null
    const epoch = this.viewerEpoch
    this.rerunBusy = true
    this.rerunError = ''
    this.rerunMessage = ''
    try {
      await this.api.rerunGeneration(job.id, index)
      if (epoch !== this.viewerEpoch || this.job?.id !== job.id) return
      // Reload this group so the discard mark and the new following entry are visible.
      await this.loadGroup(this.groupOffset, this.imageIndex)
      runInAction(() => {
        this.rerunMessage = `已提交重跑（同提示词、新随机种子）${index !== null ? '，原图已标记弃置（可恢复）' : ''}。新图会排在本条之后，按 → 查看。`
      })
    } catch (error) {
      runInAction(() => { this.rerunError = errorText(error) })
    } finally {
      runInAction(() => { this.rerunBusy = false })
    }
  }

  async move(direction: -1 | 1): Promise<void> {
    await this.step(direction)
    // In review mode keep going the same way past discarded images (bounded).
    for (let hops = 0; this.hideDiscarded && this.currentDiscarded && hops < 2000; hops += 1) {
      if (direction === -1 ? !this.canPrevious : !this.canNext) break
      await this.step(direction)
    }
  }

  private async step(direction: -1 | 1): Promise<void> {
    if (direction === -1 ? !this.canPrevious : !this.canNext) return
    const index = this.imageIndex + direction
    if (index >= 0 && index < this.imageSlots) {
      await this.loadGroup(this.groupOffset, index)
    } else if (direction === -1) {
      await this.loadGroup(this.groupOffset - 1, 'last')
    } else if (this.nextGroupOffset !== null) {
      await this.loadGroup(this.nextGroupOffset)
    }
  }

  /** Opens one group/image of the current experiment, e.g. from the review grid. */
  async showGroup(offset: number, image = 0): Promise<void> {
    if (this.selection?.kind !== 'experiment' || !Number.isSafeInteger(offset) || offset < 0) return
    await this.loadGroup(offset, image)
  }

  async retry(): Promise<void> {
    if (this.loading || !this.selection) return
    await this.loadGroup(this.groupOffset, this.requestedImage)
  }

  private async loadGroup(offset: number, requestedImage: number | 'last' = 0): Promise<void> {
    const selection = this.selection
    if (!selection) return
    const epoch = ++this.viewerEpoch
    this.viewerController?.abort()
    const controller = new AbortController()
    this.viewerController = controller
    this.releaseImage()
    this.discardError = ''
    this.rerunError = ''
    this.rerunMessage = ''
    this.groupOffset = offset
    this.requestedImage = requestedImage
    this.job = null
    this.nextGroupOffset = null
    this.imageIndex = 0
    this.loading = true
    this.imageLoading = false
    this.error = ''
    this.imageError = ''
    try {
      let job: GenerationView | undefined
      let summary: ExperimentSummary | null = null
      let nextOffset: number | null = null
      if (selection.kind === 'experiment') {
        const page = await this.api.experiment(selection.id, offset, 1, controller.signal)
        job = page.items[0]
        summary = page.summary
        nextOffset = page.next_offset
        if (summary.id !== selection.id || (job && job.parameters.experiment?.id !== selection.id)) {
          throw new ApiFailure(0, 'invalid_response', '实验记录不匹配，请重新打开。')
        }
      } else {
        job = await this.api.generation(selection.id, controller.signal)
      }
      if (epoch !== this.viewerEpoch) return
      if (!job) throw new ApiFailure(404, 'not_found', '没有可查看的实验组。')
      runInAction(() => {
        this.job = job
        this.summary = summary
        this.nextGroupOffset = nextOffset
        this.imageIndex = requestedImage === 'last' ? this.imageSlots - 1 : Math.min(requestedImage, this.imageSlots - 1)
        this.loading = false
      })
      await this.loadSelectedImage(epoch, controller.signal)
      if (job.status === 'queued' || job.status === 'running') {
        // Re-runs finish in the background; refresh this entry until it settles.
        setTimeout(() => { if (epoch === this.viewerEpoch) void this.retry() }, 5000)
      }
    } catch (error) {
      if (epoch === this.viewerEpoch) runInAction(() => { this.error = errorText(error) })
    } finally {
      if (epoch === this.viewerEpoch) runInAction(() => { this.loading = false })
    }
  }

  private async loadSelectedImage(epoch: number, signal: AbortSignal): Promise<void> {
    if (epoch !== this.viewerEpoch) return
    this.pruneExpiredImages()
    const job = this.job
    const index = this.imageIndex
    const path = job?.status === 'succeeded' ? job.image_urls[index] : undefined
    if (!job || !path) return
    this.imageLoading = true
    try {
      const expiresAt = job.result_expires_at
      if (expiresAt !== null && expiresAt <= Date.now() / 1000) {
        throw new ApiFailure(404, 'image_unavailable', 'This result image has expired.')
      }
      let url = this.cachedImage(path, expiresAt)
      if (!url) {
        const blob = await this.api.image(path, signal)
        if (epoch !== this.viewerEpoch) return
        if (expiresAt !== null && expiresAt <= Date.now() / 1000) {
          throw new ApiFailure(404, 'image_unavailable', 'This result image has expired.')
        }
        // A completed read can only populate this still-open viewer's cache.
        url = this.cachedImage(path, expiresAt) ?? this.retainImage(path, blob, expiresAt)
      }
      runInAction(() => {
        this.image = { url, index, filename: `generation-${job.id}-${job.effective_seed}-${index + 1}.png` }
      })
    } catch (error) {
      if (epoch === this.viewerEpoch) runInAction(() => { this.imageError = errorText(error) })
    } finally {
      if (epoch === this.viewerEpoch) runInAction(() => { this.imageLoading = false })
    }
  }

  private cachedImage(path: string, expiresAt: number | null): string | null {
    this.pruneExpiredImages()
    let cached = this.imageCache.get(path)
    const transient = this.transientImage
    // Explicit preload may make an already displayed oversized PNG cacheable.
    // Transfer its existing URL rather than downloading/owning it a second time.
    if (!cached && transient?.path === path && expiresAt !== null && Number.isFinite(expiresAt)
      && transient.expiresAt !== null && Number.isFinite(transient.expiresAt)
      && Math.min(expiresAt, transient.expiresAt) > Date.now() / 1000
      && this.imageCache.size < this.cacheLimit && this.imageCacheBytes + transient.size <= this.cacheByteLimit) {
      cached = { url: transient.url, size: transient.size, expiresAt: Math.min(expiresAt, transient.expiresAt) }
      this.imageCache.set(path, cached)
      this.imageCacheBytes += transient.size
      this.transientImage = null
    }
    if (!cached) return null
    if (expiresAt === null || !Number.isFinite(expiresAt)) {
      this.removeCachedImage(path)
      return null
    }
    // A metadata refresh never extends the original cached lifetime.
    cached.expiresAt = Math.min(cached.expiresAt, expiresAt)
    if (cached.expiresAt <= Date.now() / 1000) {
      this.removeCachedImage(path)
      return null
    }
    this.imageCache.delete(path)
    this.imageCache.set(path, cached)
    return cached.url
  }

  private retainImage(path: string, blob: Blob, expiresAt: number | null): string {
    this.pruneExpiredImages()
    if (expiresAt !== null && expiresAt <= Date.now() / 1000) {
      throw new ApiFailure(404, 'image_unavailable', 'This result image has expired.')
    }
    let cacheable = expiresAt !== null && Number.isFinite(expiresAt) && expiresAt > Date.now() / 1000
      && blob.size <= this.cacheByteLimit
    if (cacheable) {
      while (this.imageCache.size >= this.cacheLimit || this.imageCacheBytes + blob.size > this.cacheByteLimit) {
        // The visible cached URL remains valid until navigation releases its reference.
        const oldest = [...this.imageCache].find(([, entry]) => entry.url !== this.image?.url)
        if (!oldest) { cacheable = false; break }
        this.removeCachedImage(oldest[0])
      }
    }
    const url = URL.createObjectURL(blob)
    if (cacheable && expiresAt !== null) {
      this.imageCache.set(path, { url, size: blob.size, expiresAt })
      this.imageCacheBytes += blob.size
    } else {
      // Uncacheable images belong only to the current display.
      this.transientImage = { path, url, size: blob.size, expiresAt }
    }
    return url
  }

  private retainPreloadedImage(path: string, blob: Blob, expiresAt: number): boolean {
    this.pruneExpiredImages()
    if (expiresAt <= Date.now() / 1000) {
      throw new ApiFailure(404, 'image_unavailable', 'This result image has expired.')
    }
    if (this.imageCache.size >= this.cacheLimit || this.imageCacheBytes + blob.size > this.cacheByteLimit) return false
    // Background reads never create display-owned/transient URLs or evict entries.
    const url = URL.createObjectURL(blob)
    this.imageCache.set(path, { url, size: blob.size, expiresAt })
    this.imageCacheBytes += blob.size
    return true
  }

  private removeCachedImage(path: string): void {
    const cached = this.imageCache.get(path)
    if (!cached) return
    this.imageCache.delete(path)
    this.imageCacheBytes -= cached.size
    if (this.image?.url === cached.url) this.image = null
    URL.revokeObjectURL(cached.url)
  }

  private pruneExpiredImages(): void {
    const now = Date.now() / 1000
    for (const [path, cached] of this.imageCache) {
      if (cached.expiresAt <= now) this.removeCachedImage(path)
    }
  }

  private releaseImage(): void {
    if (this.transientImage) URL.revokeObjectURL(this.transientImage.url)
    this.transientImage = null
    this.image = null
  }

  close(): void {
    this.viewerEpoch += 1
    this.preloadEpoch += 1
    this.viewerController?.abort()
    this.preloadController?.abort()
    this.viewerController = null
    this.preloadController = null
    this.preloadCacheEnabled = false
    this.releaseImage()
    for (const path of this.imageCache.keys()) this.removeCachedImage(path)
    this.selection = null
    this.summary = null
    this.job = null
    this.groupOffset = 0
    this.nextGroupOffset = null
    this.imageIndex = 0
    this.requestedImage = 0
    this.loading = false
    this.imageLoading = false
    this.error = ''
    this.imageError = ''
    this.preloadStatus = 'idle'
    this.preloadGroupLimit = null
    this.preloadProcessedGroups = 0
    this.preloadProcessedImages = 0
    this.preloadSkippedGroups = 0
    this.preloadFailedImages = 0
    this.preloadError = ''
    this.preloadImageError = ''
  }

  reset(): void {
    this.close()
    this.listEpoch += 1
    this.listController?.abort()
    this.listController = null
    this.experiments = []
    this.listOffset = 0
    this.nextListOffset = null
    this.listLoaded = false
    this.listLoading = false
    this.listError = ''
  }
}
