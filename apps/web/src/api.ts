export interface UserInfo {
  id: string
  label: string
}

export interface GenerationRequest {
  positive_prompt: string
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
}

export interface HistoryPage {
  items: HistoryItem[]
  next_offset: number | null
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
      provider_auth_error: '图像服务认证失败，请联系管理员。',
      provider_rate_limited: '图像服务限流，请稍后重试。',
      provider_error: '图像服务处理失败，请检查参数后重试。',
      invalid_request: '图像服务拒绝了参数，请检查模型和采样器。',
      unsupported_setting: '模型或采样器不受支持，请修改后重试。',
      insufficient_balance: '图像服务余额不足，请联系管理员。',
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

  submit(parameters: GenerationRequest): Promise<GenerationAccepted> {
    return this.request('/api/generations', { method: 'POST', body: JSON.stringify(parameters) })
  }

  generation(id: string, signal?: AbortSignal): Promise<GenerationView> {
    return this.request(`/api/generations/${encodeURIComponent(id)}`, { signal })
  }

  history(offset: number, limit = 20): Promise<HistoryPage> {
    return this.request(`/api/generations?offset=${offset}&limit=${limit}`)
  }

  deleteGeneration(id: string): Promise<void> {
    return this.request(`/api/generations/${encodeURIComponent(id)}`, { method: 'DELETE' })
  }

  search(query: string): Promise<SearchResults> {
    return this.request('/api/tags/search', {
      method: 'POST',
      body: JSON.stringify({ query, limit: 10 }),
    })
  }

  advice(input: string): Promise<{ suggestion: string }> {
    return this.request('/api/advice', { method: 'POST', body: JSON.stringify({ input }) })
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
