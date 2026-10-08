import { makeAutoObservable, runInAction } from 'mobx'
import {
  ApiFailure,
  errorText,
  type GenerationRequest,
  type GenerationView,
  type HistoryItem,
  type TagCandidate,
  type UserInfo,
  WorkspaceApi,
} from './api'

export type GenerationDraft = Omit<GenerationRequest, 'width' | 'height' | 'steps' | 'cfg_scale' | 'seed' | 'sample_count'> & {
  width: string
  height: string
  steps: string
  cfg_scale: string
  seed: string
  sample_count: string
}

export function emptyDraft(): GenerationDraft {
  return {
    positive_prompt: '', negative_prompt: '', model: '', width: '1024', height: '1024',
    steps: '28', cfg_scale: '5', sampler: '', seed: '', sample_count: '1', quality: true,
  }
}

function integer(value: string, label: string, min: number, max: number, multiple = 1): number {
  const number = Number(value)
  if (!/^\d+$/.test(value) || !Number.isInteger(number) || number < min || number > max || number % multiple !== 0) {
    throw new Error(`${label}须为 ${min}-${max}${multiple > 1 ? `，且为 ${multiple} 的倍数` : ''}。`)
  }
  return number
}

export function requestFromDraft(draft: GenerationDraft): GenerationRequest {
  if (!draft.positive_prompt.trim()) throw new Error('请输入正向提示词。')
  if (draft.positive_prompt.length > 3000 || draft.negative_prompt.length > 3000) throw new Error('提示词不能超过 3000 字符。')
  if (!draft.model.trim() || draft.model.length > 80) throw new Error('请输入模型 ID（最多 80 字符）。')
  if (!draft.sampler.trim() || draft.sampler.length > 80) throw new Error('请输入采样器 ID（最多 80 字符）。')
  const cfgScale = Number(draft.cfg_scale)
  if (!draft.cfg_scale.trim() || !Number.isFinite(cfgScale) || cfgScale < 0 || cfgScale > 20) throw new Error('CFG 系数须为 0-20。')
  return {
    positive_prompt: draft.positive_prompt,
    negative_prompt: draft.negative_prompt,
    model: draft.model.trim(),
    width: integer(draft.width, '宽度', 64, 2048, 64),
    height: integer(draft.height, '高度', 64, 2048, 64),
    steps: integer(draft.steps, '步数', 1, 50),
    cfg_scale: cfgScale,
    sampler: draft.sampler.trim(),
    seed: draft.seed.trim() ? integer(draft.seed, '种子', 1, 4294967295) : null,
    sample_count: integer(draft.sample_count, '张数', 1, 8),
    quality: draft.quality,
  }
}

export class AuthStore {
  user: UserInfo | null = null
  status: 'checking' | 'guest' | 'loading' | 'ready' | 'error' = 'checking'
  error = ''
  loggingOut = false
  private epoch = 0

  constructor(
    private readonly api: WorkspaceApi,
    private readonly onEnd: () => void,
    private readonly onLogoutStart: () => void,
  ) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  async restore(): Promise<void> {
    const epoch = ++this.epoch
    this.api.advanceSession()
    this.status = 'checking'
    this.error = ''
    try {
      const user = await this.api.session()
      if (epoch === this.epoch) runInAction(() => { this.user = user; this.status = 'ready' })
    } catch (error) {
      if (epoch !== this.epoch) return
      runInAction(() => {
        this.status = error instanceof ApiFailure && error.status === 401 ? 'guest' : 'error'
        this.error = this.status === 'error' ? errorText(error) : ''
      })
    }
  }

  async login(token: string): Promise<void> {
    const epoch = ++this.epoch
    this.api.advanceSession()
    this.status = 'loading'
    this.error = ''
    try {
      const user = await this.api.login(token)
      if (epoch === this.epoch) runInAction(() => { this.user = user; this.status = 'ready' })
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => { this.status = 'guest'; this.error = errorText(error) })
    }
  }

  async logout(): Promise<void> {
    if (this.loggingOut) return
    const epoch = ++this.epoch
    this.api.advanceSession()
    this.loggingOut = true
    this.error = ''
    this.onLogoutStart()
    try {
      await this.api.logout()
      if (epoch === this.epoch) this.end('')
    } catch (error) {
      if (epoch === this.epoch && this.status === 'ready') runInAction(() => { this.error = errorText(error) })
    } finally {
      if (epoch === this.epoch) runInAction(() => { this.loggingOut = false })
    }
  }

  expire(): void {
    this.epoch += 1
    this.api.advanceSession()
    this.end('会话已过期或被撤销，请重新输入访问令牌。')
  }

  private end(message: string): void {
    this.user = null
    this.status = 'guest'
    this.error = message
    this.loggingOut = false
    this.onEnd()
  }
}

export interface ResultImage {
  url: string
  filename: string
  index: number
}

export class GenerationStore {
  draft = emptyDraft()
  job: GenerationView | null = null
  activeId: string | null = null
  images: ResultImage[] = []
  busy = false
  checking = false
  submitUncertain = false
  error = ''
  imageError = ''
  private pollTimer: ReturnType<typeof setTimeout> | null = null
  private controller: AbortController | null = null
  private epoch = 0

  constructor(private readonly api: WorkspaceApi, private readonly onSubmitted: () => void) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  setField<Key extends keyof GenerationDraft>(key: Key, value: GenerationDraft[Key]): void {
    this.draft[key] = value
  }

  setResolution(width: string, height: string): void {
    this.draft.width = width
    this.draft.height = height
  }

  insertTag(tag: string, target: 'positive_prompt' | 'negative_prompt'): void {
    const current = this.draft[target].trim()
    this.draft[target] = current ? `${current.replace(/,\s*$/, '')}, ${tag}` : tag
  }

  reuse(item: HistoryItem): void {
    this.draft = {
      ...item.parameters,
      width: String(item.parameters.width), height: String(item.parameters.height),
      steps: String(item.parameters.steps), cfg_scale: String(item.parameters.cfg_scale),
      seed: String(item.effective_seed), sample_count: String(item.parameters.sample_count),
    }
    this.error = ''
  }

  async submit(): Promise<void> {
    if (this.busy || this.activeId || this.submitUncertain) return
    this.error = ''
    let parameters: GenerationRequest
    try {
      parameters = requestFromDraft(this.draft)
    } catch (error) {
      this.error = error instanceof Error ? error.message : '生成参数无效。'
      return
    }
    this.clearResult()
    const epoch = this.epoch
    this.busy = true
    try {
      const accepted = await this.api.submit(parameters)
      if (epoch !== this.epoch) return
      runInAction(() => { this.busy = false; this.activeId = accepted.id })
      this.onSubmitted()
      await this.refresh(accepted.id)
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => {
        this.busy = false
        this.submitUncertain = !(error instanceof ApiFailure) || error.status >= 500
        this.error = this.submitUncertain
          ? '提交结果未知。请先检查历史记录，再决定是否重新提交。'
          : errorText(error)
      })
    }
  }

  async refresh(id = this.activeId ?? this.job?.id): Promise<void> {
    if (!id || this.checking) return
    const epoch = this.epoch
    if (this.pollTimer) clearTimeout(this.pollTimer)
    this.pollTimer = null
    this.controller?.abort()
    this.controller = new AbortController()
    this.checking = true
    this.error = ''
    try {
      const job = await this.api.generation(id, this.controller.signal)
      if (epoch !== this.epoch) return
      runInAction(() => {
        this.job = job
        this.checking = false
        this.activeId = job.status === 'queued' || job.status === 'running' ? job.id : null
      })
      if (job.status === 'queued' || job.status === 'running') {
        this.pollTimer = setTimeout(() => { void this.refresh(id) }, 2000)
      } else if (job.status === 'succeeded' && job.image_urls.length) {
        await this.loadImages(job, epoch)
      } else if (job.status === 'failed') {
        runInAction(() => { this.error = errorText(new ApiFailure(0, job.error_code ?? 'generation_failed', '生成失败，请检查服务状态。')) })
      }
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => {
        this.checking = false
        if (error instanceof ApiFailure && error.status === 404) this.activeId = null
        this.error = errorText(error)
      })
    }
  }

  private async loadImages(job: GenerationView, epoch: number): Promise<void> {
    const missing = job.image_urls.flatMap((path, index) => this.images.some(image => image.index === index)
      ? [] : [{ path, index }])
    const results = await Promise.allSettled(missing.map(image => this.api.image(image.path, this.controller?.signal)))
    if (epoch !== this.epoch) return
    const images = results.flatMap((result, index) => result.status === 'fulfilled'
      ? [{ url: URL.createObjectURL(result.value), filename: `generation-${job.effective_seed}-${missing[index].index + 1}.png`, index: missing[index].index }]
      : [])
    runInAction(() => {
      this.images = [...this.images, ...images].sort((left, right) => left.index - right.index)
      this.imageError = results.some(result => result.status === 'rejected')
        ? '部分图像已过期或暂不可用，请下载仍可查看的图像。'
        : ''
    })
  }

  clearResult(): void {
    this.epoch += 1
    this.controller?.abort()
    this.controller = null
    if (this.pollTimer) clearTimeout(this.pollTimer)
    this.pollTimer = null
    this.images.forEach(image => URL.revokeObjectURL(image.url))
    this.images = []
    this.job = null
    this.activeId = null
    this.checking = false
    this.imageError = ''
  }

  suspendForLogout(): void {
    const submissionPending = this.busy
    this.clearResult()
    this.busy = false
    if (submissionPending) {
      this.submitUncertain = true
      this.error = '提交结果未知。请先检查历史记录，再决定是否重新提交。'
    }
  }

  reset(): void {
    this.clearResult()
    this.draft = emptyDraft()
    this.busy = false
    this.submitUncertain = false
    this.error = ''
  }

  resume(id: string): void {
    if (this.activeId || this.busy) return
    this.clearResult()
    this.activeId = id
    void this.refresh(id)
  }

  acknowledgeUncertain(): void {
    this.submitUncertain = false
    this.error = ''
  }
}

export class HistoryStore {
  items: HistoryItem[] = []
  offset = 0
  nextOffset: number | null = null
  loading = false
  deletingId: string | null = null
  error = ''
  private epoch = 0
  private sessionVersion = 0

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  async load(offset = this.offset): Promise<void> {
    const epoch = ++this.epoch
    this.loading = true
    this.error = ''
    try {
      const page = await this.api.history(offset)
      if (epoch !== this.epoch) return
      runInAction(() => {
        this.items = page.items
        this.offset = offset
        this.nextOffset = page.next_offset
        this.loading = false
      })
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => { this.loading = false; this.error = errorText(error) })
    }
  }

  async delete(id: string): Promise<void> {
    if (this.deletingId !== null) return
    const sessionVersion = this.sessionVersion
    this.deletingId = id
    this.error = ''
    try {
      await this.api.deleteGeneration(id)
      if (sessionVersion !== this.sessionVersion) return
      const previous = this.items.length === 1 && this.offset > 0 ? Math.max(0, this.offset - 20) : this.offset
      await this.load(previous)
    } catch (error) {
      if (sessionVersion === this.sessionVersion) runInAction(() => { this.error = errorText(error) })
    } finally {
      if (sessionVersion === this.sessionVersion) runInAction(() => { this.deletingId = null })
    }
  }

  reset(): void {
    this.epoch += 1
    this.sessionVersion += 1
    this.items = []
    this.offset = 0
    this.nextOffset = null
    this.loading = false
    this.deletingId = null
    this.error = ''
  }
}

export class TagStore {
  query = ''
  results: TagCandidate[] = []
  loading = false
  searched = false
  error = ''
  retrySeconds = 0
  private epoch = 0
  private retryTimer: ReturnType<typeof setInterval> | null = null

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  setQuery(query: string): void {
    this.epoch += 1
    this.query = query
    this.results = []
    this.searched = false
    this.loading = false
    this.error = ''
  }

  async search(): Promise<void> {
    if (this.loading || this.retrySeconds > 0) return
    const query = this.query.trim()
    if (!query || query.length > 100) {
      this.error = '请输入搜索词（最多 100 字符）。'
      return
    }
    const epoch = ++this.epoch
    this.loading = true
    this.error = ''
    this.results = []
    try {
      const response = await this.api.search(query)
      if (epoch !== this.epoch) return
      runInAction(() => { this.results = response.results; this.searched = true; this.loading = false })
    } catch (error) {
      if (epoch !== this.epoch) return
      runInAction(() => {
        this.loading = false
        this.error = errorText(error)
        if (error instanceof ApiFailure && error.retryAfterSeconds) this.startRetry(error.retryAfterSeconds)
      })
    }
  }

  private startRetry(seconds: number): void {
    if (this.retryTimer) clearInterval(this.retryTimer)
    const retryAt = Date.now() + seconds * 1000
    this.retrySeconds = seconds
    this.retryTimer = setInterval(() => {
      runInAction(() => { this.retrySeconds = Math.max(0, Math.ceil((retryAt - Date.now()) / 1000)) })
      if (this.retrySeconds === 0 && this.retryTimer) {
        clearInterval(this.retryTimer)
        this.retryTimer = null
      }
    }, 250)
  }

  reset(): void {
    this.epoch += 1
    if (this.retryTimer) clearInterval(this.retryTimer)
    this.retryTimer = null
    this.query = ''
    this.results = []
    this.loading = false
    this.searched = false
    this.error = ''
    this.retrySeconds = 0
  }
}

export class AdviceStore {
  input = ''
  output = ''
  loading = false
  error = ''
  private epoch = 0

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  setInput(input: string): void { this.input = input }

  async submit(): Promise<void> {
    const input = this.input.trim()
    if (!input || input.length > 4000) {
      this.error = '请输入咨询内容（最多 4000 字符）。'
      return
    }
    const epoch = ++this.epoch
    this.output = ''
    this.error = ''
    this.loading = true
    try {
      const response = await this.api.advice(input)
      if (epoch === this.epoch) runInAction(() => { this.output = response.suggestion; this.loading = false })
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => { this.error = errorText(error); this.loading = false })
    }
  }

  reset(): void {
    this.epoch += 1
    this.input = ''
    this.output = ''
    this.loading = false
    this.error = ''
  }
}

export class AppStore {
  readonly api: WorkspaceApi
  readonly auth: AuthStore
  readonly generation: GenerationStore
  readonly history: HistoryStore
  readonly tags: TagStore
  readonly advice: AdviceStore

  constructor(fetcher: typeof fetch = fetch) {
    this.api = new WorkspaceApi(fetcher, () => this.auth.expire())
    this.auth = new AuthStore(this.api, () => this.resetProtected(), () => this.generation.suspendForLogout())
    this.history = new HistoryStore(this.api)
    this.generation = new GenerationStore(this.api, () => { void this.history.load(0) })
    this.tags = new TagStore(this.api)
    this.advice = new AdviceStore(this.api)
  }

  resetProtected(): void {
    this.generation.reset()
    this.history.reset()
    this.tags.reset()
    this.advice.reset()
  }

  dispose(): void {
    this.generation.clearResult()
    this.tags.reset()
  }
}
