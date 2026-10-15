import { makeAutoObservable, runInAction } from 'mobx'
import { ApiFailure, errorText, type ExperimentSummary, type GenerationView, WorkspaceApi } from './api'

type SavedSelection = { kind: 'generation' | 'experiment'; id: string }

interface SavedImage {
  url: string
  filename: string
  index: number
}

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
  image: SavedImage | null = null
  loading = false
  imageLoading = false
  error = ''
  imageError = ''
  private listEpoch = 0
  private viewerEpoch = 0
  private requestedImage: number | 'last' = 0
  private listController: AbortController | null = null
  private viewerController: AbortController | null = null

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

  async move(direction: -1 | 1): Promise<void> {
    if (direction === -1 ? !this.canPrevious : !this.canNext) return
    const index = this.imageIndex + direction
    if (index >= 0 && index < this.imageSlots) {
      const epoch = ++this.viewerEpoch
      this.viewerController?.abort()
      const controller = new AbortController()
      this.viewerController = controller
      this.releaseImage()
      this.imageIndex = index
      this.requestedImage = index
      this.imageError = ''
      await this.loadSelectedImage(epoch, controller.signal)
    } else if (direction === -1) {
      await this.loadGroup(this.groupOffset - 1, 'last')
    } else if (this.nextGroupOffset !== null) {
      await this.loadGroup(this.nextGroupOffset)
    }
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
    } catch (error) {
      if (epoch === this.viewerEpoch) runInAction(() => { this.error = errorText(error) })
    } finally {
      if (epoch === this.viewerEpoch) runInAction(() => { this.loading = false })
    }
  }

  private async loadSelectedImage(epoch: number, signal: AbortSignal): Promise<void> {
    const job = this.job
    const index = this.imageIndex
    const path = job?.status === 'succeeded' ? job.image_urls[index] : undefined
    if (!job || !path) return
    this.imageLoading = true
    try {
      const blob = await this.api.image(path, signal)
      if (epoch !== this.viewerEpoch) return
      const url = URL.createObjectURL(blob)
      runInAction(() => {
        this.image = { url, index, filename: `generation-${job.id}-${job.effective_seed}-${index + 1}.png` }
      })
    } catch (error) {
      if (epoch === this.viewerEpoch) runInAction(() => { this.imageError = errorText(error) })
    } finally {
      if (epoch === this.viewerEpoch) runInAction(() => { this.imageLoading = false })
    }
  }

  private releaseImage(): void {
    if (this.image) URL.revokeObjectURL(this.image.url)
    this.image = null
  }

  close(): void {
    this.viewerEpoch += 1
    this.viewerController?.abort()
    this.viewerController = null
    this.releaseImage()
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
