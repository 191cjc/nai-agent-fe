import { makeAutoObservable, runInAction } from 'mobx'
import { ApiFailure, errorText, type PromptSnapshot, type PromptSnapshotCreate, type PromptSnapshotSummary, WorkspaceApi } from './api'

const snapshotError = (error: unknown) => error instanceof ApiFailure && error.status === 404 ? '快照不存在或已被删除。' : errorText(error)

/** Private in-memory library. Pages and details are fetched only on explicit use. */
export class PromptSnapshotStore {
  items: PromptSnapshotSummary[] = []
  offset = 0
  nextOffset: number | null = null
  loading = false
  saving = false
  deletingId: string | null = null
  listError = ''
  mutationError = ''
  detailErrors = new Map<string, string>()
  loadingDetails = new Set<string>()
  private details = new Map<string, PromptSnapshot>()
  private epoch = 0
  private listVersion = 0
  private listController: AbortController | null = null
  private detailControllers = new Map<string, AbortController>()
  private mutationController: AbortController | null = null

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  get sessionEpoch(): number { return this.epoch }

  async load(offset = this.offset): Promise<void> {
    const epoch = this.epoch
    const version = ++this.listVersion
    this.listController?.abort()
    const controller = new AbortController()
    this.listController = controller
    this.loading = true
    this.listError = ''
    try {
      const page = await this.api.promptSnapshots(offset, controller.signal)
      if (epoch !== this.epoch || version !== this.listVersion) return
      runInAction(() => { this.items = page.items; this.offset = offset; this.nextOffset = page.next_offset })
    } catch (error) {
      if (epoch === this.epoch && version === this.listVersion) runInAction(() => { this.listError = errorText(error) })
    } finally {
      if (epoch === this.epoch && version === this.listVersion) runInAction(() => { this.loading = false; this.listController = null })
    }
  }

  async detail(id: string, fresh = false): Promise<PromptSnapshot | null> {
    const cached = this.details.get(id)
    if (!fresh && cached) {
      this.details.delete(id)
      this.details.set(id, cached)
      return cached
    }
    const epoch = this.epoch
    this.detailControllers.get(id)?.abort()
    const controller = new AbortController()
    this.detailControllers.set(id, controller)
    this.loadingDetails.add(id)
    this.detailErrors.delete(id)
    const current = () => epoch === this.epoch && this.detailControllers.get(id) === controller
    try {
      const snapshot = await this.api.promptSnapshot(id, controller.signal)
      if (!current()) return null
      runInAction(() => {
        this.details.delete(id)
        this.details.set(id, snapshot)
        while (this.details.size > 40) {
          const oldest = this.details.keys().next().value
          if (oldest === undefined) break
          this.details.delete(oldest)
        }
      })
      return snapshot
    } catch (error) {
      if (current()) runInAction(() => { this.details.delete(id); this.detailErrors.set(id, snapshotError(error)) })
      return null
    } finally {
      if (current()) runInAction(() => { this.loadingDetails.delete(id); this.detailControllers.delete(id) })
    }
  }

  async save(value: PromptSnapshotCreate): Promise<PromptSnapshot | null> {
    if (this.saving || this.deletingId !== null) return null
    const epoch = this.epoch
    const controller = new AbortController()
    this.mutationController = controller
    this.saving = true
    this.mutationError = ''
    try {
      const snapshot = await this.api.savePromptSnapshot(value, controller.signal)
      if (epoch !== this.epoch) return null
      await this.load(0)
      return epoch === this.epoch ? snapshot : null
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => { this.mutationError = snapshotError(error) })
      return null
    } finally {
      if (epoch === this.epoch) runInAction(() => { this.saving = false; this.mutationController = null })
    }
  }

  async delete(id: string): Promise<boolean> {
    if (this.saving || this.deletingId !== null) return false
    const epoch = this.epoch
    const controller = new AbortController()
    this.mutationController = controller
    this.deletingId = id
    this.mutationError = ''
    this.detailControllers.get(id)?.abort()
    this.detailControllers.delete(id)
    this.loadingDetails.delete(id)
    try {
      await this.api.deletePromptSnapshot(id, controller.signal)
      if (epoch !== this.epoch) return false
      runInAction(() => { this.details.delete(id); this.detailErrors.delete(id) })
      await this.load(this.items.length === 1 && this.offset > 0 ? Math.max(0, this.offset - 20) : this.offset)
      return epoch === this.epoch
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => { this.mutationError = snapshotError(error) })
      return false
    } finally {
      if (epoch === this.epoch) runInAction(() => { this.deletingId = null; this.mutationController = null })
    }
  }

  clearMutationError(): void { this.mutationError = '' }

  reset(): void {
    this.epoch += 1
    this.listVersion += 1
    this.listController?.abort()
    this.detailControllers.forEach(controller => controller.abort())
    this.mutationController?.abort()
    this.listController = null
    this.mutationController = null
    this.detailControllers.clear()
    this.details.clear()
    this.detailErrors.clear()
    this.loadingDetails.clear()
    this.items = []
    this.offset = 0
    this.nextOffset = null
    this.loading = false
    this.saving = false
    this.deletingId = null
    this.listError = ''
    this.mutationError = ''
  }
}
