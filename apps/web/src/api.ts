import { isSnapshot, isSnapshotPage, validRequestSections, type PromptSections, type PromptSnapshot, type PromptSnapshotCreate, type PromptSnapshotPage } from './prompt-sections'
export type { PromptSections, PromptSnapshot, PromptSnapshotCreate, PromptSnapshotEntry, PromptSnapshotSummary, PromptSnapshotPage } from './prompt-sections'

export interface UserInfo {
  id: string
  label: string
}

export interface AccountBalance {
  fixed: number
  purchased: number
  total: number
  fetched_at: number
}

export interface CharacterPrompt {
  prompt: string
  x?: number
  y?: number
}

export interface ExperimentWeight {
  tag_index: number
  label: string
  weight: string
}

export interface DatasetItem {
  id: string
  /** Shared scene; on multi-person items each person lives in `characters`. */
  prompt: string
  characters?: CharacterPrompt[]
}

export interface ReferenceImageUse {
  id: string
  sha256: string
}

/** Frozen reference images for one character dataset group; bytes stay on the server. */
export interface ReferenceUse {
  mode: 'vibe' | 'img2img' | 'gpt' | 'precise'
  images: ReferenceImageUse[]
  strength?: number | null
  noise?: number | null
  information_extracted?: number | null
  reference_strength?: number | null
  gpt_quality?: 'low' | 'medium' | 'high' | null
  /** Precise Reference only (NovelAI director reference, V4.5). */
  precise_type?: PreciseType | null
  precise_strength?: number | null
  precise_fidelity?: number | null
}

export type PreciseType = 'character' | 'style' | 'character&style'

export interface Capabilities {
  gpt_image: boolean
  gpt_image_model: string | null
}

export interface ReferenceImage {
  id: string
  sha256: string
  mime_type: 'image/png' | 'image/jpeg'
  width: number
  height: number
  byte_size: number
  source: 'upload' | 'result'
  created_at: number
}

export interface CharacterRunRequest {
  traits: string
  mode: 'vibe' | 'img2img' | 'gpt' | 'precise'
  reference_ids: string[]
  strength?: number
  noise?: number
  information_extracted?: number
  reference_strength?: number
  gpt_quality?: 'low' | 'medium' | 'high'
  precise_type?: PreciseType
  precise_strength?: number
  precise_fidelity?: number
}

export interface CharacterRunPlan {
  traits: string
  mode: 'vibe' | 'img2img' | 'gpt' | 'precise'
  references: ReferenceImageUse[]
  strength?: number | null
  noise?: number | null
  information_extracted?: number | null
  reference_strength?: number | null
  gpt_quality?: 'low' | 'medium' | 'high' | null
  precise_type?: PreciseType | null
  precise_strength?: number | null
  precise_fidelity?: number | null
}

export interface ExperimentContext {
  id: string
  ordinal: string
  total: string
  /** Absent for style weight groups; dataset groups carry one item and no weights. */
  kind?: 'dataset'
  item?: DatasetItem
  weights: ExperimentWeight[]
  /** Dataset only: an owner re-run of this ordinal (new random seed); names the replaced job. */
  rerun_of?: string
}

export interface GenerationRequest {
  prompt_comments?: boolean
  positive_prompt: string
  style_prompt: string
  character_prompts: CharacterPrompt[]
  auto_character_position?: boolean
  negative_prompt: string
  model: string
  width: number
  height: number
  steps: number
  cfg_scale: number
  sampler: string
  seed: number | null
  sample_count: number
  quality: boolean
  experiment?: ExperimentContext | null
  prompt_sections?: PromptSections | null
  reference?: ReferenceUse | null
}

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface HistoryItem {
  id: string
  parameters: GenerationRequest
  status: JobStatus
  created_at: number
  updated_at: number
  effective_seed: number
  error_code: string | null
  image_count: number
}

export interface GenerationView extends HistoryItem {
  image_urls: string[]
  result_expires_at: number | null
  provider_request: Record<string, unknown> | null
  /** Owner review marks: exports skip these image indexes. */
  discarded_images?: number[]
}

export interface HistoryPage {
  items: HistoryItem[]
  next_offset: number | null
}

export type ExperimentKind = 'style' | 'dataset'

export interface ExperimentSummary {
  id: string
  kind?: ExperimentKind
  total: string
  group_count: number
  completed_count: number
  image_count: number
  created_at: number
  updated_at: number
}

export interface ExperimentPage {
  items: ExperimentSummary[]
  next_offset: number | null
}

export interface ExperimentDetailPage {
  summary: ExperimentSummary
  items: GenerationView[]
  next_offset: number | null
}

export interface ExperimentRunRange {
  tag_index: number
  min: string
  max: string
  step: string
}

export interface ExperimentRunDefinition {
  id: string
  kind?: ExperimentKind
  parameters: GenerationRequest
  ranges: ExperimentRunRange[]
  items?: DatasetItem[]
  styles?: string[] | null
  /** Request shape on create; the server answers with the frozen CharacterRunPlan. */
  character?: CharacterRunRequest | CharacterRunPlan | null
}

export interface ExperimentRunState extends ExperimentRunDefinition {
  status: 'running' | 'stopping' | 'stopped' | 'completed'
  total: string
  next_ordinal: string
  processed_count: string
  succeeded_count: string
  failed_count: string
  current_ordinal: string | null
  current_job_id: string | null
  seed: number
  sample_count: number
  created_at: number
  updated_at: number
  error_code: string | null
}

export interface GenerationAccepted {
  id: string
  status: JobStatus
}

export interface TagCandidate {
  tag: string
  cn_name?: string | null
  category?: string | null
  is_nsfw?: boolean | null
  count?: number | null
  score?: number | null
  summary?: string | null
}

export interface SearchResults {
  results: TagCandidate[]
  source_url?: string
}

interface ErrorBody {
  code: string
  message: string
  retryable?: boolean
}

function readErrorBody(value: unknown): Partial<ErrorBody> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return {}
  const fields = value as Record<string, unknown>
  return {
    code: typeof fields.code === 'string' ? fields.code : undefined,
    message: typeof fields.message === 'string' ? fields.message : undefined,
    retryable: fields.retryable === true,
  }
}

function checkedRun(value: ExperimentRunState): ExperimentRunState {
  const decimal = (field: unknown, positive = false, maxDigits = 1000) => typeof field === 'string' && field.length <= maxDigits
    && (positive ? /^[1-9]\d*$/ : /^(0|[1-9]\d*)$/).test(field)
  const parameters = value?.parameters
  const valid = value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value.id)
    && ['running', 'stopping', 'stopped', 'completed'].includes(value.status)
    && decimal(value.total, true) && decimal(value.next_ordinal, true, 1001)
    && decimal(value.processed_count) && decimal(value.succeeded_count) && decimal(value.failed_count)
    && (value.current_ordinal === null || decimal(value.current_ordinal, true))
    && (value.current_job_id === null || typeof value.current_job_id === 'string')
    && Number.isInteger(value.seed) && value.seed >= 1 && value.seed <= 4294967295
    && Number.isInteger(value.sample_count) && value.sample_count >= 1 && value.sample_count <= 8
    && Number.isFinite(value.created_at) && Number.isFinite(value.updated_at)
    && (value.error_code === null || typeof value.error_code === 'string')
    && parameters && typeof parameters.style_prompt === 'string' && typeof parameters.positive_prompt === 'string'
    && typeof parameters.negative_prompt === 'string' && typeof parameters.model === 'string' && typeof parameters.sampler === 'string'
    && typeof parameters.quality === 'boolean' && Number.isFinite(parameters.cfg_scale)
    && (parameters.auto_character_position === undefined || typeof parameters.auto_character_position === 'boolean')
    && [parameters.width, parameters.height, parameters.steps, parameters.sample_count].every(Number.isInteger)
    && (parameters.seed === null || Number.isInteger(parameters.seed))
    && Array.isArray(parameters.character_prompts) && parameters.character_prompts.every(character => character && typeof character.prompt === 'string'
      && (character.x === undefined || Number.isFinite(character.x)) && (character.y === undefined || Number.isFinite(character.y)))
    && validRequestSections(parameters)
    && (value.kind === undefined || value.kind === 'style' || value.kind === 'dataset')
    && Array.isArray(value.ranges) && (value.kind === 'dataset' ? value.ranges.length === 0 : value.ranges.length > 0)
    && value.ranges.every(range => range && Number.isInteger(range.tag_index)
      && typeof range.min === 'string' && typeof range.max === 'string' && typeof range.step === 'string')
    && (value.kind !== 'dataset' || (Array.isArray(value.items) && value.items.length > 0
      && value.items.every(item => item && typeof item.id === 'string' && typeof item.prompt === 'string'
        && (item.characters === undefined || (Array.isArray(item.characters) && item.characters.every(character => character && typeof character.prompt === 'string'))))))
  if (!valid) throw new ApiFailure(0, 'invalid_response', '实验响应无效，请重新连接核对。')
  return value
}

function checkedHistoryItem<T extends HistoryItem>(item: T): T {
  if (!item?.parameters || !validRequestSections(item.parameters)) throw new ApiFailure(0, 'invalid_response', '保存的提示词分区无效，请重新加载。')
  return item
}

export class ApiFailure extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly retryable = false,
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message)
  }
}

function retryAfterSeconds(value: string | null): number | null {
  if (!value) return null
  if (/^\d+$/.test(value)) return Math.min(Number(value), 86400)
  const date = Date.parse(value)
  return Number.isFinite(date) ? Math.min(86400, Math.max(0, Math.ceil((date - Date.now()) / 1000))) : null
}

export function errorText(error: unknown): string {
  if (error instanceof ApiFailure) {
    const messages: Record<string, string> = {
      invalid_token: '令牌无效或已撤销。',
      unauthenticated: '会话已失效，请重新登录。',
      forbidden_origin: '访问来源不匹配，请使用配置的 HTTPS 地址。',
      validation_error: '输入不符合要求，请检查参数。',
      rate_limited: '请求过于频繁，请稍后重试。',
      queue_full: '生成队列已满，请稍后重试。',
      provider_unavailable: '图像服务暂不可用，请联系管理员。',
      result_storage_unavailable: '图片保存空间暂不可用，本次未提交生成，请稍后再试或联系管理员。',
      result_storage_error: '图片保存失败，请检查历史记录；请勿自动重新生成。',
      experiment_conflict: '这组画风实验已经提交或实验信息不一致，请先检查历史记录。',
      experiment_run_active: '已有进行中的画风实验或训练集批跑，请查看其进度或手动停止。',
      experiment_run_conflict: '实验编号已被其他定义使用，请检查已保存的实验。',
      prompt_snapshot_conflict: '此快照编号已用于其他内容，请关闭后重新保存。',
      experiment_run_unknown: '实验提交结果未知，请重新连接核对，不要重复开始。',
      experiment_run_missing: '尚未找到这次实验，提交结果仍待确认；请检查历史后再次连接。',
      rerun_unsupported: '只有训练集里的图片可以重跑。',
      experiment_active: '这条记录属于进行中的画风实验，请先停止实验或等待完成后删除。',
      provider_auth_error: '图像服务认证失败，请联系管理员。',
      provider_rate_limited: '图像服务限流，请稍后重试。',
      provider_error: '图像服务处理失败，请检查参数后重试。',
      invalid_request: '图像服务拒绝了参数，请检查模型和采样器。',
      unsupported_setting: '模型或采样器不受支持，请修改后重试。',
      unsupported_character_prompts: '当前图像服务不支持独立人物提示词，请联系管理员。',
      unsupported_auto_character_position: '当前图像服务不支持自动人物位置，请选择手动位置或联系管理员。',
      insufficient_balance: '图像服务余额不足，请联系管理员。',
      balance_unavailable: '图像服务余额暂不可用，请稍后刷新。',
      balance_auth_error: '余额查询认证失败，请联系管理员。',
      balance_rate_limited: '余额查询过于频繁，请稍后刷新。',
      balance_timeout: '余额查询超时，请稍后刷新。',
      balance_bad_response: '余额查询响应无效，请稍后刷新。',
      outcome_unknown: '任务结果未知，请先检查历史记录。',
      generation_failed: '生成失败，请检查服务状态。',
      not_found: '任务或图像不存在，可能已过期。',
      image_unavailable: '图像已过期或暂不可用。',
      invalid_image: '图像格式无效。',
      invalid_image_path: '图像地址无效。',
      job_active: '任务仍在运行，暂时无法删除。',
      search_busy: '标签搜索繁忙，请稍后重试。',
      search_rate_limited: '标签搜索限流，请稍后重试。',
      search_timeout: '标签搜索超时，请重试。',
      search_unavailable: '标签搜索暂不可用，请重试。',
      search_auth_error: '标签搜索认证失败，请联系管理员。',
      advice_busy: '建议服务繁忙，请稍后重试。',
      advice_timeout: '建议服务超时，请重试。',
      advice_unavailable: '建议服务暂不可用，请重试。',
      advice_failed: '建议生成失败，请重试。',
      advice_image_unsupported: '当前 AI 模型不支持读取图片，请更换支持图片的模型。',
      reference_too_large: '参考图超过 8 MB。',
      invalid_reference_image: '仅支持 PNG 或 JPEG，且宽高需在 64–2048 像素之间。',
      unsupported_media_type: '仅支持 PNG 或 JPEG 图片。',
      reference_quota_exceeded: '参考图已达上限（20 张 / 128 MB），请先删除不用的参考图。',
      reference_in_use: '这张参考图正被进行中的批跑使用，结束后才能删除。',
      reference_not_found: '参考图不存在或已删除，请重新选择。',
      reference_unavailable: '参考图已被删除或内容变化，本条已跳过。',
      unsupported_reference_mode: 'NovelAI 服务不支持该参考图模式（精准参考需要 MCP 服务提供 director_reference_* 参数）。',
      gpt_image_unavailable: 'GPT 生图未配置（服务器缺少 NAI_GPT_IMAGE_API_KEY）。',
      content_policy: '被 GPT 内容审核拒绝，本条已跳过。',
      not_ready: '服务暂不可用，请稍后重试。',
    }
    const detail = messages[error.code] ?? error.message
    return error.retryAfterSeconds === null ? detail : `${detail} ${error.retryAfterSeconds} 秒后可重试。`
  }
  return error instanceof Error && error.name === 'AbortError'
    ? '请求已取消。'
    : '无法连接服务，请检查网络后重试。'
}

export class WorkspaceApi {
  private sessionVersion = 0
  private readonly webBasePath = import.meta.env.BASE_URL.replace(/\/$/, '')

  constructor(
    private readonly fetcher: typeof fetch = fetch,
    private readonly onUnauthorized: () => void = () => {},
  ) {}

  advanceSession(): void {
    this.sessionVersion += 1
  }

  private async request<T>(path: string, init: RequestInit = {}, skipUnauthorized = false): Promise<T> {
    const version = this.sessionVersion
    const response = await this.fetcher.call(globalThis, `${this.webBasePath}${path}`, {
      ...init,
      credentials: 'include',
      cache: 'no-store',
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    })
    if (!response.ok) {
      let body: Partial<ErrorBody> = {}
      try {
        body = readErrorBody(await response.json() as unknown)
      } catch {
        body = {}
      }
      if (response.status === 401 && !skipUnauthorized && version === this.sessionVersion) this.onUnauthorized()
      throw new ApiFailure(
        response.status,
        typeof body.code === 'string' ? body.code : 'request_error',
        typeof body.message === 'string' ? body.message : `Request failed (${response.status}).`,
        body.retryable === true,
        retryAfterSeconds(response.headers.get('Retry-After')),
      )
    }
    return response.status === 204 ? undefined as T : await response.json() as T
  }

  session(): Promise<UserInfo> {
    return this.request('/api/auth/session', {}, true)
  }

  login(token: string): Promise<UserInfo> {
    return this.request('/api/auth/session', { method: 'POST', body: JSON.stringify({ token }) }, true)
  }

  logout(): Promise<void> {
    return this.request('/api/auth/session', { method: 'DELETE' })
  }

  async balance(signal?: AbortSignal): Promise<AccountBalance> {
    const value = await this.request<unknown>('/api/account/balance', { signal })
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      const fields = value as Record<string, unknown>
      const count = (field: unknown): field is number => typeof field === 'number' && Number.isSafeInteger(field) && field >= 0
      if (Object.keys(fields).length === 4 && count(fields.fixed) && count(fields.purchased)
        && count(fields.total) && count(fields.fetched_at)
        && Number.isSafeInteger(fields.fixed + fields.purchased) && fields.total === fields.fixed + fields.purchased) {
        return { fixed: fields.fixed, purchased: fields.purchased, total: fields.total, fetched_at: fields.fetched_at }
      }
    }
    throw new ApiFailure(0, 'balance_bad_response', '余额查询响应无效，请稍后刷新。')
  }

  submit(parameters: GenerationRequest): Promise<GenerationAccepted> {
    return this.request('/api/generations', { method: 'POST', body: JSON.stringify(parameters) })
  }

  async generation(id: string, signal?: AbortSignal): Promise<GenerationView> {
    return checkedHistoryItem(await this.request<GenerationView>(`/api/generations/${encodeURIComponent(id)}`, { signal }))
  }

  async history(offset: number, limit = 20, manualOnly = false): Promise<HistoryPage> {
    const page = await this.request<HistoryPage>(`/api/generations?offset=${offset}&limit=${limit}${manualOnly ? '&manual_only=true' : ''}`)
    page.items.forEach(checkedHistoryItem)
    return page
  }

  experiments(offset = 0, limit = 20, signal?: AbortSignal): Promise<ExperimentPage> {
    return this.request(`/api/style-experiments?offset=${offset}&limit=${limit}`, { signal })
  }

  async experiment(id: string, offset = 0, limit = 1, signal?: AbortSignal): Promise<ExperimentDetailPage> {
    const page = await this.request<ExperimentDetailPage>(`/api/style-experiments/${encodeURIComponent(id)}?offset=${offset}&limit=${limit}`, { signal })
    page.items.forEach(checkedHistoryItem)
    return page
  }

  async promptSnapshots(offset = 0, signal?: AbortSignal): Promise<PromptSnapshotPage> {
    const page = await this.request<unknown>(`/api/prompt-snapshots?limit=20&offset=${offset}`, { signal })
    if (!isSnapshotPage(page)) throw new ApiFailure(0, 'invalid_response', '快照列表无效，请重新加载。')
    return page
  }

  async promptSnapshot(id: string, signal?: AbortSignal): Promise<PromptSnapshot> {
    const snapshot = await this.request<unknown>(`/api/prompt-snapshots/${encodeURIComponent(id)}`, { signal })
    if (!isSnapshot(snapshot) || snapshot.id !== id) throw new ApiFailure(0, 'invalid_response', '快照内容无效，请重新加载。')
    return snapshot
  }

  async savePromptSnapshot(snapshot: PromptSnapshotCreate, signal?: AbortSignal): Promise<PromptSnapshot> {
    const saved = await this.request<unknown>('/api/prompt-snapshots', { method: 'POST', body: JSON.stringify(snapshot), signal })
    if (!isSnapshot(saved) || saved.id !== snapshot.id) throw new ApiFailure(0, 'invalid_response', '快照保存结果无效，请刷新列表核对。')
    return saved
  }

  deletePromptSnapshot(id: string, signal?: AbortSignal): Promise<void> {
    return this.request(`/api/prompt-snapshots/${encodeURIComponent(id)}`, { method: 'DELETE', signal })
  }

  async createExperimentRun(definition: ExperimentRunDefinition, signal?: AbortSignal): Promise<ExperimentRunState> {
    const run = checkedRun(await this.request<ExperimentRunState>('/api/style-experiment-runs', { method: 'POST', body: JSON.stringify(definition), signal }))
    if (run.id !== definition.id) throw new ApiFailure(0, 'invalid_response', '实验编号不匹配，请重新连接核对。')
    return run
  }

  async createDatasetRun(definition: ExperimentRunDefinition, signal?: AbortSignal): Promise<ExperimentRunState> {
    const body = {
      id: definition.id, parameters: definition.parameters, items: definition.items,
      ...(definition.styles ? { styles: definition.styles } : {}),
      ...(definition.character ? { character: definition.character } : {}),
    }
    const run = checkedRun(await this.request<ExperimentRunState>('/api/dataset-runs', { method: 'POST', body: JSON.stringify(body), signal }))
    if (run.id !== definition.id || run.kind !== 'dataset') throw new ApiFailure(0, 'invalid_response', '实验编号不匹配，请重新连接核对。')
    return run
  }

  async activeExperimentRun(signal?: AbortSignal): Promise<{ run: ExperimentRunState | null }> {
    const response = await this.request<{ run: ExperimentRunState | null }>('/api/style-experiment-runs/active', { signal })
    return { run: response?.run === null ? null : checkedRun(response?.run) }
  }

  async experimentRun(id: string, signal?: AbortSignal): Promise<ExperimentRunState> {
    const run = checkedRun(await this.request<ExperimentRunState>(`/api/style-experiment-runs/${encodeURIComponent(id)}`, { signal }))
    if (run.id !== id) throw new ApiFailure(0, 'invalid_response', '实验编号不匹配，请重新连接核对。')
    return run
  }

  async stopExperimentRun(id: string, signal?: AbortSignal): Promise<ExperimentRunState> {
    const run = checkedRun(await this.request<ExperimentRunState>(`/api/style-experiment-runs/${encodeURIComponent(id)}/stop`, { method: 'POST', signal }))
    if (run.id !== id) throw new ApiFailure(0, 'invalid_response', '实验编号不匹配，请重新连接核对。')
    return run
  }

  setImageDiscarded(jobId: string, index: number, discarded: boolean): Promise<void> {
    return this.request(`/api/generations/${encodeURIComponent(jobId)}/images/${index}/discard`, { method: discarded ? 'PUT' : 'DELETE' })
  }

  /** One paid generation: the same training-set group, one sample, a new random seed. */
  rerunGeneration(jobId: string, discardIndex: number | null): Promise<GenerationAccepted> {
    return this.request(`/api/generations/${encodeURIComponent(jobId)}/rerun`, {
      method: 'POST', body: JSON.stringify(discardIndex === null ? {} : { discard_index: discardIndex }),
    })
  }

  deleteGeneration(id: string): Promise<void> {
    return this.request(`/api/generations/${encodeURIComponent(id)}`, { method: 'DELETE' })
  }

  search(query: string, signal?: AbortSignal): Promise<SearchResults> {
    return this.request('/api/tags/search', {
      method: 'POST',
      body: JSON.stringify({ query, limit: 10 }),
      signal,
    })
  }

  capabilities(signal?: AbortSignal): Promise<Capabilities> {
    return this.request('/api/capabilities', { signal })
  }

  referenceImages(signal?: AbortSignal): Promise<{ items: ReferenceImage[] }> {
    return this.request('/api/reference-images', { signal })
  }

  uploadReferenceImage(file: Blob, signal?: AbortSignal): Promise<ReferenceImage> {
    return this.request('/api/reference-images', {
      method: 'POST', body: file, headers: { 'Content-Type': file.type }, signal,
    })
  }

  referenceFromResult(jobId: string, imageIndex: number, signal?: AbortSignal): Promise<ReferenceImage> {
    return this.request('/api/reference-images/from-result', {
      method: 'POST', body: JSON.stringify({ job_id: jobId, image_index: imageIndex }), signal,
    })
  }

  deleteReferenceImage(id: string): Promise<void> {
    return this.request(`/api/reference-images/${encodeURIComponent(id)}`, { method: 'DELETE' })
  }

  async referenceImage(id: string, signal?: AbortSignal): Promise<Blob> {
    if (!/^[0-9a-f-]{36}$/.test(id)) throw new ApiFailure(0, 'invalid_image_path', 'Invalid reference image.')
    const version = this.sessionVersion
    const response = await this.fetcher.call(globalThis, `${this.webBasePath}/api/reference-images/${id}/image`, { credentials: 'include', cache: 'no-store', signal })
    if (response.status === 401) {
      if (version === this.sessionVersion) this.onUnauthorized()
      throw new ApiFailure(401, 'session_expired', 'Session expired.')
    }
    if (!response.ok) throw new ApiFailure(response.status, 'image_unavailable', 'Reference image is unavailable.')
    return response.blob()
  }

  traitAdvice(referenceIds: string[], traits: string, signal?: AbortSignal): Promise<{ suggestion: string }> {
    return this.request('/api/reference-images/trait-advice', {
      method: 'POST', body: JSON.stringify({ reference_ids: referenceIds, traits }), signal,
    })
  }

  advice(input: string, signal?: AbortSignal): Promise<{ suggestion: string }> {
    return this.request('/api/advice', { method: 'POST', body: JSON.stringify({ input }), signal })
  }

  async image(path: string, signal?: AbortSignal): Promise<Blob> {
    if (!/^\/api\/generation-results\/[0-9a-f-]+\/images\/\d+$/.test(path)) {
      throw new ApiFailure(0, 'invalid_image_path', 'Invalid result image path.')
    }
    const version = this.sessionVersion
    const response = await this.fetcher.call(globalThis, `${this.webBasePath}${path}`, { credentials: 'include', cache: 'no-store', signal })
    if (response.status === 401) {
      if (version === this.sessionVersion) this.onUnauthorized()
      throw new ApiFailure(401, 'session_expired', 'Session expired.')
    }
    if (!response.ok) throw new ApiFailure(response.status, 'image_unavailable', 'This result image has expired or is unavailable.')
    const blob = await response.blob()
    if (blob.type !== 'image/png') throw new ApiFailure(0, 'invalid_image', 'Unexpected image format.')
    return blob
  }
}
