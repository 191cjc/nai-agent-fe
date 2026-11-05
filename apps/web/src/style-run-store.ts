import { makeAutoObservable, runInAction } from 'mobx'
import { copyPromptMetadata } from './prompt-sections'
import { ApiFailure, errorText, type CharacterRunRequest, type DatasetItem, type ExperimentRunDefinition, type ExperimentRunRange, type ExperimentRunState, type GenerationRequest, WorkspaceApi } from './api'

/** Runs that left the queue this session, shown until dismissed. */
const MAX_FINISHED = 5

/**
 * Observes the owner's server-side run queue. Several runs may be unfinished at once:
 * each lane (NovelAI / GPT) executes its oldest run and the rest wait. Detaching never
 * sends a stop request.
 */
export class StyleRunStore {
  /** Unfinished runs, oldest first, as last reported by the server. */
  runs: ExperimentRunState[] = []
  /** Runs that completed or stopped while observed, newest first. */
  finished: ExperimentRunState[] = []
  /** Create request whose outcome is not yet known (submitting or unconfirmed). */
  definition: ExperimentRunDefinition | null = null
  pendingId: string | null = null
  initialized = false
  creating = false
  checking = false
  connected = false
  missing = false
  error = ''
  /** Definite refusal of the latest create (e.g. queue full); kept until the next create. */
  createError = ''
  stopError = ''
  stoppingIds: string[] = []
  private observing = false
  private epoch = 0
  private requestVersion = 0
  private controller: AbortController | null = null
  private timer: ReturnType<typeof setTimeout> | null = null

  constructor(private readonly api: WorkspaceApi, private readonly onProgress: () => void) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  get running(): boolean {
    return this.runs.length > 0
  }

  get activeIds(): string[] {
    return this.runs.map(run => run.id)
  }

  /** Only an unknown create outcome blocks new submissions; running runs just queue. */
  get locked(): boolean {
    return !this.initialized || this.creating || this.pendingId !== null
  }

  get kind(): 'style' | 'dataset' {
    return this.definition?.kind ?? 'style'
  }

  /** The definition being submitted, so its form can show what was frozen. */
  get snapshot(): ExperimentRunDefinition | null {
    return this.definition
  }

  enterWorkspace(): void {
    if (this.observing) return
    this.observing = true
    void this.refresh()
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

  private static changed(previous: ExperimentRunState, next: ExperimentRunState): boolean {
    return previous.processed_count !== next.processed_count || previous.current_job_id !== next.current_job_id
      || previous.in_flight_count !== next.in_flight_count || previous.parallelism !== next.parallelism
      || previous.status !== next.status
  }

  private finish(run: ExperimentRunState): void {
    this.finished = [run, ...this.finished.filter(item => item.id !== run.id)].slice(0, MAX_FINISHED)
  }

  /** Replace the queue; returns ids that left it so their final state can be fetched. */
  private acceptQueue(runs: ExperimentRunState[]): string[] {
    const previous = new Map(this.runs.map(run => [run.id, run]))
    const current = new Set(runs.map(run => run.id))
    const left = this.runs.filter(run => !current.has(run.id)).map(run => run.id)
    const progressed = left.length > 0 || runs.some(run => {
      const before = previous.get(run.id)
      return before ? StyleRunStore.changed(before, run) : this.initialized
    })
    this.runs = runs
    this.stoppingIds = this.stoppingIds.filter(id => current.has(id))
    this.initialized = true
    this.connected = true
    if (progressed) this.onProgress()
    return left
  }

  /** Merge one run (create/stop/reconcile answer) into the queue or the finished list. */
  private acceptRun(run: ExperimentRunState): void {
    const index = this.runs.findIndex(item => item.id === run.id)
    const before = index >= 0 ? this.runs[index] : null
    const unfinished = run.status === 'running' || run.status === 'stopping'
    if (unfinished) {
      if (before) this.runs[index] = { ...run, name: run.name ?? before.name }
      else this.runs.push(run)
    } else {
      if (before) this.runs.splice(index, 1)
      this.finish({ ...run, name: run.name ?? before?.name })
    }
    if (!before || StyleRunStore.changed(before, run)) this.onProgress()
  }

  private schedule(): void {
    if (!this.observing || !this.connected || this.creating) return
    if (!this.runs.length && !this.pendingId) return
    if (this.timer) clearTimeout(this.timer)
    this.timer = setTimeout(() => { this.timer = null; void this.refresh() }, 2000)
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
  async startDataset(parameters: GenerationRequest, items: DatasetItem[], extra: { styles?: string[]; character?: CharacterRunRequest; name?: string; gptConcurrency?: number } = {}): Promise<void> {
    if (this.locked || !this.observing) return
    const id = this.newRunId()
    if (!id) return
    await this.create({
      id, kind: 'dataset', parameters: StyleRunStore.frozenParameters(parameters), ranges: [],
      items: items.map(item => ({ ...item })),
      ...(extra.styles ? { styles: [...extra.styles] } : {}),
      ...(extra.character ? { character: { ...extra.character, reference_ids: [...extra.character.reference_ids] } } : {}),
      ...(extra.name?.trim() ? { name: extra.name.trim() } : {}),
      ...(extra.gptConcurrency ? { gpt_concurrency: extra.gptConcurrency } : {}),
    })
  }

  private async create(definition: ExperimentRunDefinition): Promise<void> {
    const id = definition.id
    const { epoch, version, controller } = this.beginRequest()
    this.definition = definition
    this.pendingId = id
    this.creating = true
    this.missing = false
    this.error = ''
    this.createError = ''
    this.stopError = ''
    let reconcile = false
    try {
      const run = definition.kind === 'dataset'
        ? await this.api.createDatasetRun(definition, controller.signal)
        : await this.api.createExperimentRun(definition, controller.signal)
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => {
        this.pendingId = null
        this.definition = null
        this.acceptRun({ ...run, name: run.name ?? definition.name ?? null })
      })
    } catch (error) {
      if (!this.isCurrent(epoch, version)) return
      runInAction(() => {
        const definite = error instanceof ApiFailure && error.status >= 400 && error.status < 500
        if (definite) this.createError = errorText(error)
        else this.error = '实验提交结果未知，正在按实验编号只读核对；不会重复提交。'
        if (definite) {
          this.pendingId = null
          this.definition = null
        } else reconcile = true
      })
    } finally {
      if (this.isCurrent(epoch, version)) runInAction(() => { this.creating = false; this.schedule() })
    }
    if (reconcile && this.observing && epoch === this.epoch) await this.refresh()
  }

  /** Read the queue, confirm an unknown create, and settle runs that left the queue. */
  async refresh(): Promise<void> {
    if (!this.observing || this.creating) return
    const { epoch, version, controller } = this.beginRequest()
    this.checking = true
    const pendingId = this.pendingId
    try {
      const runs = await this.api.queuedExperimentRuns(controller.signal)
      if (!this.isCurrent(epoch, version)) return
      const left = runInAction(() => {
        this.error = ''
        return this.acceptQueue(runs)
      })
      const lookups = [...left, ...(pendingId && !runs.some(run => run.id === pendingId) ? [pendingId] : [])]
      for (const id of lookups) {
        let run: ExperimentRunState | null = null
        let failure: unknown = null
        try { run = await this.api.experimentRun(id, controller.signal) } catch (error) { failure = error }
        if (!this.isCurrent(epoch, version)) return
        runInAction(() => {
          if (id === pendingId) {
            if (run) this.acceptRun(run)
            else {
              this.missing = failure instanceof ApiFailure && failure.status === 404
              this.error = this.missing
                ? '尚未找到这次实验，提交结果仍待确认。请检查历史记录后重新连接；不会重复提交。'
                : `实验提交结果仍未确认。${errorText(failure)} 请重新连接核对。`
            }
          } else if (run) this.finish(run)
        })
        if (id === pendingId && run) runInAction(() => { this.pendingId = null; this.definition = null; this.missing = false })
      }
      if (pendingId && runs.some(run => run.id === pendingId)) runInAction(() => {
        this.pendingId = null
        this.definition = null
        this.missing = false
      })
    } catch (error) {
      if (this.isCurrent(epoch, version)) runInAction(() => {
        this.connected = false
        this.error = pendingId
          ? `实验提交结果仍未确认。${errorText(error)} 请重新连接核对。`
          : `实验队列连接中断，服务器可能仍在运行。${errorText(error)} 请重新连接或手动停止。`
      })
    } finally {
      if (this.isCurrent(epoch, version)) runInAction(() => { this.checking = false; this.schedule() })
    }
  }

  isStopping(id: string): boolean {
    return this.stoppingIds.includes(id)
  }

  async stop(id: string): Promise<void> {
    if (!this.observing || this.isStopping(id)) return
    const epoch = this.epoch
    this.stoppingIds.push(id)
    this.stopError = ''
    try {
      const run = await this.api.stopExperimentRun(id)
      if (epoch !== this.epoch || !this.observing) return
      runInAction(() => { this.acceptRun(run) })
    } catch (error) {
      if (epoch === this.epoch && this.observing) runInAction(() => {
        this.stopError = `停止请求未确认，服务器可能仍在运行。${errorText(error)} 可刷新队列或再次手动停止。`
      })
    } finally {
      if (epoch === this.epoch) runInAction(() => {
        this.stoppingIds = this.stoppingIds.filter(item => item !== id)
        this.schedule()
      })
    }
  }

  /** Change an unfinished GPT run's concurrency; in-flight items are never cancelled. */
  async setParallelism(id: string, parallelism: number): Promise<string> {
    if (!this.observing) return ''
    const epoch = this.epoch
    try {
      const run = await this.api.setRunParallelism(id, parallelism)
      if (epoch === this.epoch && this.observing) runInAction(() => { this.acceptRun(run) })
      return ''
    } catch (error) {
      return errorText(error)
    }
  }

  dismissFinished(id?: string): void {
    this.finished = id ? this.finished.filter(run => run.id !== id) : []
  }

  async acknowledgeMissing(): Promise<void> {
    if (!this.missing || !this.pendingId || this.creating || this.checking) return
    this.pendingId = null
    this.definition = null
    this.missing = false
    this.error = ''
    this.stopError = ''
    await this.refresh()
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
    this.stoppingIds = []
    this.connected = false
  }

  reset(): void {
    this.detach()
    this.runs = []
    this.finished = []
    this.definition = null
    this.pendingId = null
    this.missing = false
    this.error = ''
    this.createError = ''
    this.stopError = ''
  }
}
