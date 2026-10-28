import { makeAutoObservable, runInAction } from 'mobx'
import { copyPromptMetadata } from './prompt-sections'
import { ApiFailure, errorText, type DatasetItem, type ExperimentRunDefinition, type ExperimentRunRange, type ExperimentRunState, type GenerationRequest, WorkspaceApi } from './api'

/** Observes one server-owned run. Detaching never sends a stop request. */
export class StyleRunStore {
  run: ExperimentRunState | null = null
  definition: ExperimentRunDefinition | null = null
  pendingId: string | null = null
  initialized = false
  creating = false
  checking = false
  stopping = false
  connected = false
  missing = false
  error = ''
  stopError = ''
  private observing = false
  private epoch = 0
  private requestVersion = 0
  private controller: AbortController | null = null
  private timer: ReturnType<typeof setTimeout> | null = null

  constructor(private readonly api: WorkspaceApi, private readonly onProgress: () => void) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  get running(): boolean {
    return this.run?.status === 'running' || this.run?.status === 'stopping'
  }

  get kind(): 'style' | 'dataset' {
    return (this.definition ?? this.run)?.kind ?? 'style'
  }

  get locked(): boolean {
    return !this.initialized || this.creating || this.pendingId !== null || this.running || this.stopping
  }

  get snapshot(): ExperimentRunDefinition | null {
    return this.definition ?? (this.running ? this.run : null)
  }

  enterWorkspace(): void {
    if (this.observing) return
    this.observing = true
    if (this.pendingId || this.running) void this.refresh()
    else void this.checkActive()
  }

  private beginRequest(): { epoch: number; version: number; controller: AbortController } {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
    this.controller?.abort()
    const controller = new AbortController()
    this.controller = controller
    return { epoch: this.epoch, version: ++this.requestVersion, controller }
  }

  private isCurrent(epoch: number, version: number): boolean {
    return this.observing && epoch === this.epoch && version === this.requestVersion
  }

  private accept(run: ExperimentRunState, clearStopError = false): void {
    const previous = this.run
    this.run = run
    this.pendingId = null
    this.definition = null
    this.initialized = true
    this.connected = true
    this.creating = false
    this.missing = false
    this.error = ''
    if (clearStopError || run.status !== 'running') this.stopError = ''
    // Initial attachment is independent of the one-time latest-history load.
    if (previous && (previous.id !== run.id || previous.processed_count !== run.processed_count
      || previous.current_job_id !== run.current_job_id || previous.status !== run.status)) this.onProgress()
  }

  private schedule(): void {
    if (!this.observing || !this.running || !this.connected || this.creating || this.stopping) return
    if (this.timer) clearTimeout(this.timer)
    this.timer = setTimeout(() => { this.timer = null; void this.refresh() }, 2000)
  }

  async checkActive(): Promise<void> {
    if (!this.observing || this.creating || this.stopping || this.pendingId) return
    const { epoch, version, controller } = this.beginRequest()
    this.initialized = false
    this.checking = true
    this.error = ''
    try {
      const { run } = await this.api.activeExperimentRun(controller.signal)
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => {
        if (run) this.accept(run)
        else {
          this.initialized = true
          this.connected = true
          if (this.running) this.run = null
        }
      })
    } catch (error) {
      if (this.isCurrent(epoch, version)) runInAction(() => {
        this.connected = false
        this.error = `无法确认是否有进行中的实验。${errorText(error)} 请重新连接后再生成。`
      })
    } finally {
      if (this.isCurrent(epoch, version)) runInAction(() => { this.checking = false; this.schedule() })
    }
  }

  private newRunId(): string | null {
    try { return crypto.randomUUID() } catch {
      this.error = '浏览器无法创建实验编号，请通过 HTTPS 使用支持的浏览器。'
      return null
    }
  }

  private static frozenParameters(parameters: GenerationRequest): GenerationRequest {
    return {
      ...parameters, character_prompts: parameters.character_prompts.map(character => ({ ...character })),
      ...(parameters.prompt_sections ? { prompt_sections: copyPromptMetadata(parameters.prompt_sections) } : {}),
    }
  }

  async start(parameters: GenerationRequest, ranges: ExperimentRunRange[]): Promise<void> {
    if (this.locked || !this.observing) return
    const id = this.newRunId()
    if (!id) return
    await this.create({ id, parameters: StyleRunStore.frozenParameters(parameters), ranges: ranges.map(range => ({ ...range })) })
  }

  /** Fixed-style dataset run: same single POST, reconciliation and Stop safeguards. */
  async startDataset(parameters: GenerationRequest, items: DatasetItem[]): Promise<void> {
    if (this.locked || !this.observing) return
    const id = this.newRunId()
    if (!id) return
    await this.create({
      id, kind: 'dataset', parameters: StyleRunStore.frozenParameters(parameters), ranges: [],
      items: items.map(item => ({ ...item })),
    })
  }

  private async create(definition: ExperimentRunDefinition): Promise<void> {
    const id = definition.id
    const { epoch, version, controller } = this.beginRequest()
    this.definition = definition
    this.pendingId = id
    this.run = null
    this.creating = true
    this.connected = false
    this.missing = false
    this.error = ''
    this.stopError = ''
    let reconcile = false
    let findActive = false
    try {
      const run = definition.kind === 'dataset'
        ? await this.api.createDatasetRun(definition, controller.signal)
        : await this.api.createExperimentRun(definition, controller.signal)
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => { this.accept(run) })
    } catch (error) {
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => {
        const definite = error instanceof ApiFailure && error.status >= 400 && error.status < 500
        this.error = definite ? errorText(error) : '实验提交结果未知，正在按实验编号只读核对；不会重复提交。'
        if (definite) {
          this.pendingId = null
          this.definition = null
          findActive = error.code === 'experiment_run_active'
        } else reconcile = true
      })
    } finally {
      if (this.isCurrent(epoch, version)) runInAction(() => { this.creating = false; this.schedule() })
    }
    if (!this.isCurrent(epoch, version)) return
    if (findActive) await this.checkActive()
    else if (reconcile) await this.refresh()
  }

  async refresh(): Promise<void> {
    if (!this.observing || this.creating || this.stopping) return
    const id = this.pendingId ?? this.run?.id
    if (!id) { await this.checkActive(); return }
    const { epoch, version, controller } = this.beginRequest()
    this.checking = true
    this.error = ''
    try {
      const run = await this.api.experimentRun(id, controller.signal)
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => { this.accept(run) })
    } catch (error) {
      if (this.isCurrent(epoch, version)) runInAction(() => {
        this.connected = false
        this.missing = this.pendingId !== null && error instanceof ApiFailure && error.status === 404
        this.error = this.missing
          ? '尚未找到这次实验，提交结果仍待确认。请检查历史记录后重新连接；不会重复提交。'
          : this.pendingId
            ? `实验提交结果仍未确认。${errorText(error)} 请重新连接核对。`
            : `实验进度连接中断，服务器可能仍在运行。${errorText(error)} 请重新连接或手动停止。`
      })
    } finally {
      if (this.isCurrent(epoch, version)) runInAction(() => { this.checking = false; this.schedule() })
    }
  }

  async stop(): Promise<void> {
    const id = this.pendingId ?? this.run?.id
    if (!this.observing || !id || this.creating || this.stopping || (!this.running && !this.pendingId)) return
    const { epoch, version, controller } = this.beginRequest()
    this.checking = false
    this.stopping = true
    this.stopError = ''
    try {
      const run = await this.api.stopExperimentRun(id, controller.signal)
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => { this.accept(run, true) })
    } catch (error) {
      if (this.isCurrent(epoch, version)) runInAction(() => {
        this.connected = false
        this.stopError = `停止请求未确认，服务器可能仍在运行。${errorText(error)} 可重新连接或再次手动停止。`
      })
    } finally {
      if (this.isCurrent(epoch, version)) runInAction(() => { this.stopping = false; this.schedule() })
    }
  }

  async acknowledgeMissing(): Promise<void> {
    if (!this.missing || !this.pendingId || this.creating || this.checking || this.stopping) return
    this.pendingId = null
    this.definition = null
    this.missing = false
    this.initialized = false
    this.error = ''
    this.stopError = ''
    await this.checkActive()
  }

  detach(): void {
    this.epoch += 1
    this.requestVersion += 1
    this.observing = false
    this.controller?.abort()
    this.controller = null
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
    this.initialized = false
    this.creating = false
    this.checking = false
    this.stopping = false
    this.connected = false
  }

  reset(): void {
    this.detach()
    this.run = null
    this.definition = null
    this.pendingId = null
    this.missing = false
    this.error = ''
    this.stopError = ''
  }
}
