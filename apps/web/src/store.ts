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
import {
  createStyleExperimentPlan,
  type StyleExperimentPlan,
  type StyleExperimentRange,
} from './style-experiment'
import { SavedResultsStore } from './saved-results'
import { StyleRunStore } from './style-run-store'

export const MAX_CHARACTERS = 6
export const CHARACTER_POSITION_MIN = 0.1
export const CHARACTER_POSITION_MAX = 0.9
export const CHARACTER_POSITION_CENTER = 0.5
export const NATIVE_CHARACTER_MODELS = [
  'nai-diffusion-4-full',
  'nai-diffusion-4-curated-preview',
  'nai-diffusion-4-5-full',
  'nai-diffusion-4-5-curated',
  'nai-diffusion-5-full',
  'nai-diffusion-5-curated',
] as const

export interface CharacterDraft {
  id: string
  prompt: string
  x: number
  y: number
}

export type PositiveTagTarget = 'style_prompt' | 'positive_prompt' | `character:${string}`

export type GenerationDraft = Omit<GenerationRequest, 'width' | 'height' | 'steps' | 'cfg_scale' | 'seed' | 'sample_count' | 'character_prompts' | 'auto_character_position' | 'experiment'> & {
  width: string
  height: string
  steps: string
  cfg_scale: string
  seed: string
  sample_count: string
  character_prompts: CharacterDraft[]
  auto_character_position: boolean
}

let characterSequence = 0

function newCharacter(prompt = '', x = CHARACTER_POSITION_CENTER, y = CHARACTER_POSITION_CENTER): CharacterDraft {
  return { id: `character-${++characterSequence}`, prompt, x, y }
}

function validCharacterPosition(value: number): boolean {
  return Number.isFinite(value) && value >= CHARACTER_POSITION_MIN && value <= CHARACTER_POSITION_MAX
}

export function supportsNativeCharacters(model: string): boolean {
  return NATIVE_CHARACTER_MODELS.some(candidate => candidate === model.trim())
}

export function emptyDraft(): GenerationDraft {
  return {
    positive_prompt: '', style_prompt: '', character_prompts: [newCharacter()], auto_character_position: false,
    negative_prompt: '', model: '', width: '1024', height: '1024',
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
  const basePrompt = draft.style_prompt.trim()
    ? [draft.style_prompt.trim(), draft.positive_prompt.trim()].filter(Boolean).join(', ')
    : draft.positive_prompt
  if (!basePrompt.trim()) throw new Error('请填写画风或公共提示词。')
  if (draft.style_prompt.length > 3000 || draft.positive_prompt.length > 3000 || basePrompt.length > 3000) {
    throw new Error('画风和公共提示词合计不能超过 3000 字符（含分隔符）。')
  }
  if (draft.negative_prompt.length > 3000) throw new Error('负面提示词不能超过 3000 字符。')
  if (draft.character_prompts.length > MAX_CHARACTERS) throw new Error(`最多添加 ${MAX_CHARACTERS} 个人物。`)
  const characters = draft.character_prompts.filter(character => character.prompt.trim())
  if (characters.some(character => character.prompt.length > 3000)) throw new Error('每个人物的提示词不能超过 3000 字符。')
  if (characters.some(character => !validCharacterPosition(character.x) || !validCharacterPosition(character.y))) {
    throw new Error('人物的 X / Y 坐标须为 0.1–0.9 之间的有效数值。')
  }
  if (!draft.model.trim() || draft.model.length > 80) throw new Error('请输入模型 ID（最多 80 字符）。')
  if (characters.length && !supportsNativeCharacters(draft.model)) {
    throw new Error('当前模型不支持独立人物，请在生成设置中选择列表中的 V4 / V4.5 / V5 模型。')
  }
  if (!draft.sampler.trim() || draft.sampler.length > 80) throw new Error('请输入采样器 ID（最多 80 字符）。')
  const cfgScale = Number(draft.cfg_scale)
  if (!draft.cfg_scale.trim() || !Number.isFinite(cfgScale) || cfgScale < 0 || cfgScale > 20) throw new Error('CFG 系数须为 0-20。')
  return {
    positive_prompt: draft.positive_prompt,
    style_prompt: draft.style_prompt,
    character_prompts: characters.map(character => ({ prompt: character.prompt, x: character.x, y: character.y })),
    auto_character_position: draft.auto_character_position,
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

/** Bound every lazily emitted context before the first paid request. */
function validateExperimentMetadata(plan: StyleExperimentPlan): void {
  if (plan.total.toString().length > 1000) throw new Error('实验组合总数不能超过 1000 位，请缩小范围。')
  if (!plan.dimensions.length || plan.dimensions.length > 1500) throw new Error('实验最多选择 1500 个画风词条。')
  let labelLength = 0
  for (const dimension of plan.dimensions) {
    if (!Number.isInteger(dimension.tagIndex) || dimension.tagIndex < 0 || dimension.tagIndex > 2999 || !dimension.label.trim()) {
      throw new Error('实验词条信息无效，请重新选择。')
    }
    labelLength += dimension.label.length
    const last = dimension.minUnits + (dimension.count - 1n) * dimension.stepUnits
    const absolute = (value: bigint) => value < 0n ? -value : value
    const largest = absolute(dimension.minUnits) > absolute(last) ? absolute(dimension.minUnits) : absolute(last)
    const integerDigits = (largest / 10n ** BigInt(dimension.places)).toString().length
    const length = dimension.count === 1n ? dimension.min.length
      : integerDigits + 1 + dimension.places + (dimension.minUnits < 0n ? 1 : 0)
    if (length > 100) throw new Error('实验权重不能超过 100 字符，请缩小数值或精度。')
  }
  if (labelLength > 3000) throw new Error('所选实验词条合计不能超过 3000 字符。')
}

interface GenerationOperation {
  token: number
  acceptedId: string | null
}

export class GenerationStore {
  draft = emptyDraft()
  positiveTagTarget: PositiveTagTarget = 'positive_prompt'
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
  private operationVersion = 0
  private draftVersion = 0
  private operation: GenerationOperation | null = null

  constructor(
    private readonly api: WorkspaceApi,
    readonly runs: StyleRunStore,
    private readonly onSubmitted: () => void,
    private readonly onTerminal: () => void,
  ) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  setField<Key extends keyof GenerationDraft>(key: Key, value: GenerationDraft[Key]): void {
    this.draftVersion += 1
    this.draft[key] = value
  }

  setResolution(width: string, height: string): void {
    this.draftVersion += 1
    this.draft.width = width
    this.draft.height = height
  }

  /** Edits and generation ownership changes invalidate pending entry restoration. */
  get entryRestoreRevision(): string {
    return `${this.draftVersion}:${this.epoch}:${this.operationVersion}`
  }

  get positiveTagTargets(): { value: PositiveTagTarget; label: string }[] {
    return [
      { value: 'style_prompt', label: '画风' },
      { value: 'positive_prompt', label: '公共' },
      ...this.draft.character_prompts.map((character, index) => ({
        value: `character:${character.id}` as const, label: `人物 ${index + 1}`,
      })),
    ]
  }

  setPositiveTagTarget(target: string): void {
    this.positiveTagTarget = this.positiveTagTargets.find(option => option.value === target)?.value ?? 'positive_prompt'
  }

  addCharacter(): string | null {
    if (this.draft.character_prompts.length >= MAX_CHARACTERS) return null
    this.draftVersion += 1
    const character = newCharacter()
    this.draft.character_prompts.push(character)
    return character.id
  }

  setCharacterPrompt(id: string, prompt: string): void {
    const character = this.draft.character_prompts.find(character => character.id === id)
    if (character) {
      this.draftVersion += 1
      character.prompt = prompt
    }
  }

  setCharacterPosition(id: string, x: number, y: number): void {
    if (!validCharacterPosition(x) || !validCharacterPosition(y)) return
    const character = this.draft.character_prompts.find(character => character.id === id)
    if (character) {
      this.draftVersion += 1
      character.x = x
      character.y = y
    }
  }

  removeCharacter(id: string): void {
    this.draftVersion += 1
    this.draft.character_prompts = this.draft.character_prompts.filter(character => character.id !== id)
    if (this.positiveTagTarget === `character:${id}`) this.positiveTagTarget = 'positive_prompt'
  }

  insertTag(tag: string, target: 'positive' | 'negative'): void {
    this.draftVersion += 1
    const append = (value: string) => {
      const current = value.trim()
      return current ? `${current.replace(/,\s*$/, '')}, ${tag}` : tag
    }
    if (target === 'negative') {
      this.draft.negative_prompt = append(this.draft.negative_prompt)
    } else if (this.positiveTagTarget === 'style_prompt' || this.positiveTagTarget === 'positive_prompt') {
      this.draft[this.positiveTagTarget] = append(this.draft[this.positiveTagTarget])
    } else {
      const character = this.draft.character_prompts.find(character => `character:${character.id}` === this.positiveTagTarget)
      if (character) character.prompt = append(character.prompt)
      else {
        this.positiveTagTarget = 'positive_prompt'
        this.draft.positive_prompt = append(this.draft.positive_prompt)
      }
    }
  }

  reuse(item: HistoryItem): void {
    this.draftVersion += 1
    const parameters = { ...item.parameters }
    // Historical experiment identity belongs to its saved run, never a draft.
    delete parameters.experiment
    this.draft = {
      ...parameters,
      style_prompt: item.parameters.style_prompt ?? '',
      auto_character_position: item.parameters.auto_character_position ?? false,
      character_prompts: item.parameters.character_prompts?.length
        ? item.parameters.character_prompts.map(character => newCharacter(character.prompt, character.x, character.y)) : [newCharacter()],
      width: String(item.parameters.width), height: String(item.parameters.height),
      steps: String(item.parameters.steps), cfg_scale: String(item.parameters.cfg_scale),
      seed: String(item.effective_seed), sample_count: String(item.parameters.sample_count),
    }
    this.positiveTagTarget = 'positive_prompt'
    this.error = ''
  }

  async submit(): Promise<void> {
    if (this.operationLocked || this.busy || this.activeId || this.submitUncertain) return
    this.error = ''
    let parameters: GenerationRequest
    try {
      parameters = requestFromDraft(this.draft)
    } catch (error) {
      this.error = error instanceof Error ? error.message : '生成参数无效。'
      return
    }
    this.clearActiveResult()
    await this.submitParameters(parameters)
  }

  get experimentRunning(): boolean {
    return this.runs.running
  }

  get operationLocked(): boolean {
    return this.ordinaryOperationLocked || this.runs.locked
  }

  get ordinaryOperationLocked(): boolean {
    return this.operation !== null
  }

  async startStyleExperiment(source: string, ranges: StyleExperimentRange[]): Promise<void> {
    if (this.operationLocked || this.busy || this.activeId || this.submitUncertain) return
    this.error = ''
    let plan: StyleExperimentPlan
    let parameters: GenerationRequest
    try {
      if (source !== this.draft.style_prompt) throw new Error('画风已变化，请重新选择实验词条。')
      parameters = requestFromDraft(this.draft)
      if (!supportsNativeCharacters(parameters.model)) throw new Error('画风实验需要列表中的 V4 / V4.5 / V5 模型。')
      plan = createStyleExperimentPlan(source, ranges)
      validateExperimentMetadata(plan)
      const shared = parameters.positive_prompt.trim()
      if (plan.canBeEmpty && !shared) throw new Error('权重为 0 时可能移除全部画风词条，请填写公共提示词，或调整范围以保留至少一个画风词条。')
      const combinedLength = plan.maxStyleLength
        ? plan.maxStyleLength - (source.length - source.trim().length) + (shared ? 2 + shared.length : 0)
        : parameters.positive_prompt.length
      if (plan.maxStyleLength > 3000 || combinedLength > 3000) {
        throw new Error('实验权重可能使画风和公共提示词超过 3000 字符，请缩短提示词或权重范围。')
      }
    } catch (error) {
      this.error = error instanceof Error ? error.message : '画风实验参数无效。'
      return
    }
    this.clearActiveResult()
    this.operationVersion += 1
    await this.runs.start(parameters, plan.dimensions.map(dimension => ({
      tag_index: dimension.tagIndex, min: dimension.min, max: dimension.max, step: dimension.step,
    })))
  }

  /** Ordinary generation only; server experiments never use this POST path. */
  private async submitParameters(parameters: GenerationRequest): Promise<void> {
    const epoch = this.epoch
    const token = ++this.operationVersion
    this.operation = { token, acceptedId: null }
    this.busy = true
    let accepted
    try {
      accepted = await this.api.submit(parameters)
    } catch (error) {
      if (epoch === this.epoch && this.operation?.token === token) runInAction(() => {
        this.busy = false
        this.operation = null
        // This exact POST refusal occurs before history creation or enqueue.
        const providerUnconfigured = error instanceof ApiFailure && error.status === 503 && error.code === 'provider_unavailable'
        const storageRefused = error instanceof ApiFailure && error.status === 503 && error.code === 'result_storage_unavailable'
        this.submitUncertain = !(error instanceof ApiFailure) || (error.status >= 500 && !providerUnconfigured && !storageRefused)
        this.error = providerUnconfigured
          ? '图像生成服务尚未配置，暂时无法生图，请联系管理员。'
          : this.submitUncertain
            ? '提交结果未知。请先检查历史记录，再决定是否重新提交。'
            : errorText(error)
      })
      return
    }
    if (epoch !== this.epoch || this.operation?.token !== token) return
    runInAction(() => {
      this.busy = false
      this.activeId = accepted.id
      this.operation!.acceptedId = accepted.id
    })
    this.onSubmitted()
    await this.refresh(accepted.id)
  }

  async refresh(id = this.activeId ?? this.job?.id): Promise<void> {
    if (!id || this.checking) return
    if (this.operation && this.operation.acceptedId !== id) return
    if (!this.operation) {
      if (this.runs.locked) return
      this.operation = { token: ++this.operationVersion, acceptedId: id }
    }
    const operationToken = this.operation.token
    const epoch = this.epoch
    if (this.pollTimer) clearTimeout(this.pollTimer)
    this.pollTimer = null
    this.controller?.abort()
    const controller = new AbortController()
    this.controller = controller
    this.checking = true
    this.error = ''
    let terminalJob: GenerationView | null = null
    try {
      const job = await this.api.generation(id, controller.signal)
      if (epoch !== this.epoch || this.operation?.token !== operationToken) return
      const firstTerminalObservation = (job.status === 'succeeded' || job.status === 'failed')
        && (this.job?.id !== job.id || this.job.status !== job.status)
      runInAction(() => {
        this.job = job
        this.activeId = job.status === 'queued' || job.status === 'running' ? job.id : null
      })
      if (firstTerminalObservation) this.onTerminal()
      if (job.status === 'queued' || job.status === 'running') {
        this.pollTimer = setTimeout(() => { void this.refresh(id) }, 2000)
      } else {
        if (job.status === 'succeeded') {
          if (job.image_urls.length) await this.loadImages(job, epoch, operationToken, controller.signal)
        } else if (job.status === 'failed') {
          runInAction(() => { this.error = errorText(new ApiFailure(0, job.error_code ?? 'generation_failed', '生成失败，请检查服务状态。')) })
        }
        terminalJob = job
      }
    } catch (error) {
      if (epoch === this.epoch && this.operation?.token === operationToken) runInAction(() => {
        this.error = errorText(error)
        // An accepted task remains owned after GET failure until explicit recheck.
        if (error instanceof ApiFailure && error.status === 404) {
          this.activeId = null
          this.operation = null
        }
      })
    } finally {
      if (epoch === this.epoch) runInAction(() => { this.checking = false })
    }
    if (terminalJob && epoch === this.epoch && this.operation?.token === operationToken) runInAction(() => { this.operation = null })
  }

  private async loadImages(job: GenerationView, epoch: number, operationToken: number, signal: AbortSignal): Promise<void> {
    const missing = job.image_urls.flatMap((path, index) => this.images.some(image => image.index === index)
      ? [] : [{ path, index }])
    const results = await Promise.allSettled(missing.map(image => this.api.image(image.path, signal)))
    if (epoch !== this.epoch || this.operation?.token !== operationToken) return
    const images: ResultImage[] = []
    try {
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') images.push({
          url: URL.createObjectURL(result.value), filename: `generation-${job.effective_seed}-${missing[index].index + 1}.png`, index: missing[index].index,
        })
      })
    } catch (error) {
      images.forEach(image => URL.revokeObjectURL(image.url))
      throw error
    }
    runInAction(() => {
      this.images = [...this.images, ...images].sort((left, right) => left.index - right.index)
      this.imageError = results.some(result => result.status === 'rejected')
        ? '部分图像已过期或暂不可用，请下载仍可查看的图像。'
        : ''
    })
  }

  private clearActiveResult(): void {
    this.epoch += 1
    this.controller?.abort()
    this.controller = null
    if (this.pollTimer) clearTimeout(this.pollTimer)
    this.pollTimer = null
    this.images.forEach(image => URL.revokeObjectURL(image.url))
    this.images = []
    this.job = null
    this.activeId = null
    this.operation = null
    this.busy = false
    this.checking = false
    this.imageError = ''
  }

  clearResult(): void {
    const submissionPending = this.busy
    this.clearActiveResult()
    if (submissionPending) {
      this.submitUncertain = true
      this.error = '提交结果未知。请先检查历史记录，再决定是否重新提交。'
    }
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
    this.draftVersion += 1
    this.draft = emptyDraft()
    this.positiveTagTarget = 'positive_prompt'
    this.busy = false
    this.submitUncertain = false
    this.error = ''
  }

  resume(id: string): void {
    if (this.operationLocked || this.activeId || this.busy) return
    this.clearActiveResult()
    this.activeId = id
    void this.refresh(id)
  }

  acknowledgeUncertain(): void {
    this.submitUncertain = false
    this.error = ''
  }
}

interface HistoryLoadResult {
  epoch: number
  items: HistoryItem[]
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
  private refreshPending = false

  constructor(private readonly api: WorkspaceApi) {
    makeAutoObservable(this, undefined, { autoBind: true })
  }

  async load(offset = this.offset): Promise<HistoryLoadResult | null> {
    const epoch = ++this.epoch
    this.loading = true
    this.error = ''
    let result: HistoryLoadResult | null = null
    try {
      const page = await this.api.history(offset)
      if (epoch !== this.epoch) return null
      runInAction(() => {
        this.items = page.items
        this.offset = offset
        this.nextOffset = page.next_offset
        this.loading = false
      })
      result = { epoch, items: page.items }
    } catch (error) {
      if (epoch === this.epoch) runInAction(() => { this.loading = false; this.error = errorText(error) })
    } finally {
      if (epoch === this.epoch && this.refreshPending) {
        runInAction(() => { this.refreshPending = false })
        // Follow the latest requested page, even if it differs from the displayed page.
        void this.load(offset)
      }
    }
    return result && this.isCurrentLoad(result) ? result : null
  }

  isCurrentLoad(result: HistoryLoadResult): boolean {
    return result.epoch === this.epoch
  }

  refresh(): void {
    if (this.loading) {
      this.refreshPending = true
      return
    }
    void this.load()
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
    this.refreshPending = false
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
  readonly savedResults: SavedResultsStore
  readonly styleRuns: StyleRunStore
  private workspaceUser: UserInfo | null = null
  private workspaceEntryVersion = 0

  constructor(fetcher: typeof fetch = fetch) {
    this.api = new WorkspaceApi(fetcher, () => this.auth.expire())
    this.auth = new AuthStore(this.api, () => this.resetProtected(), () => {
      this.workspaceEntryVersion += 1
      this.generation.suspendForLogout()
      this.styleRuns.detach()
      this.savedResults.reset()
    })
    this.savedResults = new SavedResultsStore(this.api)
    this.history = new HistoryStore(this.api)
    this.styleRuns = new StyleRunStore(this.api, () => this.history.refresh())
    this.generation = new GenerationStore(
      this.api,
      this.styleRuns,
      () => { void this.history.load(0) },
      () => this.history.refresh(),
    )
    this.tags = new TagStore(this.api)
    this.advice = new AdviceStore(this.api)
  }

  async enterWorkspace(): Promise<void> {
    const user = this.auth.user
    if (this.auth.status !== 'ready' || this.auth.loggingOut || !user) return
    // Failed logout remounts must reconnect the observer without restoring drafts again.
    this.styleRuns.enterWorkspace()
    if (this.workspaceUser === user) return
    // A failed logout or StrictMode effect replay retains this authenticated entry.
    this.workspaceUser = user
    const entryVersion = ++this.workspaceEntryVersion
    const draftRevision = this.generation.entryRestoreRevision
    const page = await this.history.load(0)
    if (!page || entryVersion !== this.workspaceEntryVersion
      || this.auth.status !== 'ready' || this.auth.loggingOut || this.auth.user !== user
      || draftRevision !== this.generation.entryRestoreRevision || !this.history.isCurrentLoad(page)
      || this.generation.ordinaryOperationLocked || this.generation.busy || this.generation.activeId
      || this.generation.checking || this.generation.submitUncertain) return
    if (page.items[0]) this.generation.reuse(page.items[0])
  }

  resetProtected(): void {
    this.workspaceEntryVersion += 1
    this.workspaceUser = null
    this.generation.reset()
    this.history.reset()
    this.tags.reset()
    this.advice.reset()
    this.savedResults.reset()
    this.styleRuns.reset()
  }

  dispose(): void {
    this.workspaceEntryVersion += 1
    this.generation.clearResult()
    this.styleRuns.reset()
    this.tags.reset()
    this.savedResults.reset()
  }
}
