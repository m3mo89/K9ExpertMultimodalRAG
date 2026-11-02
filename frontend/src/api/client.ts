import type {
  AdminCredentials,
  AnalysisFeedback,
  BreedAnalysisRequest,
  BreedAnalysisResponse,
  BreedProfile,
  CitationDetail,
  Confirmation,
  Conversation,
  ConversationSummary,
  DocumentSummary,
  DocumentVersion,
  ErrorEnvelope,
  Feedback,
  HealthReport,
  Job,
  ModelConfiguration,
  OperationalMetrics,
  PageEvidence,
  PublicationResult,
  PublicHealth,
  QueryRequest,
  QueryResponse,
  ReindexProgress,
  UploadResult,
} from './types'

/**
 * The only base the browser may call. It is same-origin and relative on purpose: the client
 * never learns model-runtime or vector-index addresses, which stay on the server's loopback.
 */
export const API_BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryable: boolean
  readonly traceId: string | null
  readonly details: unknown

  constructor(status: number, envelope: Partial<ErrorEnvelope> & { code: string }) {
    super(envelope.message ?? envelope.code)
    this.name = 'ApiError'
    this.status = status
    this.code = envelope.code
    this.retryable = envelope.retryable ?? status >= 500
    this.traceId = envelope.trace_id ?? null
    this.details = envelope.details ?? null
  }
}

type Fetch = typeof fetch

interface RequestOptions {
  method?: string
  body?: unknown
  admin?: AdminCredentials | null
  signal?: AbortSignal
}

function isEnvelope(value: unknown): value is ErrorEnvelope {
  return typeof value === 'object' && value !== null && typeof (value as ErrorEnvelope).code === 'string'
}

export class ApiClient {
  private readonly fetchImpl: Fetch

  constructor(fetchImpl: Fetch = (input, init) => globalThis.fetch(input, init)) {
    this.fetchImpl = fetchImpl
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' }
    let body: BodyInit | undefined
    if (options.body instanceof FormData) {
      body = options.body
    } else if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(options.body)
    }
    if (options.admin) {
      headers['X-K9-Admin-Secret'] = options.admin.secret
      headers['X-K9-Actor'] = options.admin.actor
    }
    let response: Response
    try {
      response = await this.fetchImpl(`${API_BASE}${path}`, {
        method: options.method ?? 'GET',
        headers,
        body,
        signal: options.signal,
        credentials: 'same-origin',
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      throw new ApiError(0, { code: 'network_unavailable', retryable: true })
    }
    const payload: unknown = await response.json().catch(() => null)
    if (!response.ok) {
      throw new ApiError(
        response.status,
        isEnvelope(payload) ? payload : { code: 'unexpected_response' },
      )
    }
    return payload as T
  }

  // Public read and query operations.
  health = () => this.request<PublicHealth>('/health')
  submitQuery = (query: QueryRequest, signal?: AbortSignal) =>
    this.request<QueryResponse>('/queries', { method: 'POST', body: query, signal })
  listConversations = () => this.request<ConversationSummary[]>('/conversations')
  createConversation = () => this.request<Conversation>('/conversations', { method: 'POST' })
  conversation = (id: string) => this.request<Conversation>(`/conversations/${encodeURIComponent(id)}`)
  citation = (id: string) => this.request<CitationDetail>(`/citations/${encodeURIComponent(id)}`)
  citationPage = (id: string, physicalPage: number) =>
    this.request<PageEvidence>(
      `/citations/${encodeURIComponent(id)}/page?physical_page=${physicalPage}`,
    )
  submitFeedback = (answerId: string, useful: boolean, comment: string | null) =>
    this.request<Feedback>(`/answers/${encodeURIComponent(answerId)}/feedback`, {
      method: 'POST',
      body: { useful, comment },
    })
  submitBreedAnalysis = (analysis: BreedAnalysisRequest, signal?: AbortSignal) =>
    this.request<BreedAnalysisResponse>('/breed-analyses', {
      method: 'POST',
      body: analysis,
      signal,
    })
  breedAnalysis = (id: string) =>
    this.request<BreedAnalysisResponse>(`/breed-analyses/${encodeURIComponent(id)}`)
  submitAnalysisFeedback = (analysisId: string, useful: boolean, comment: string | null) =>
    this.request<AnalysisFeedback>(`/breed-analyses/${encodeURIComponent(analysisId)}/feedback`, {
      method: 'POST',
      body: { useful, comment },
    })
  breedProfile = (breed: string) =>
    this.request<BreedProfile>(`/breeds/${encodeURIComponent(breed)}/profile`)
  configuration = () => this.request<ModelConfiguration>('/configuration')
  listDocuments = () => this.request<DocumentSummary[]>('/documents')
  listVersions = (documentId: string) =>
    this.request<DocumentVersion[]>(`/documents/${encodeURIComponent(documentId)}/versions`)

  // Administrative operations; every call carries the local administrative secret.
  uploadDocument = (
    admin: AdminCredentials,
    file: File,
    metadata: { title: string; author?: string; category?: string },
  ) => {
    const form = new FormData()
    form.append('file', file)
    form.append('title', metadata.title)
    if (metadata.author) form.append('author', metadata.author)
    if (metadata.category) form.append('category', metadata.category)
    return this.request<UploadResult>('/documents', { method: 'POST', body: form, admin })
  }
  replaceDocument = (admin: AdminCredentials, documentId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return this.request<UploadResult>(`/documents/${encodeURIComponent(documentId)}/versions`, {
      method: 'POST',
      body: form,
      admin,
    })
  }
  job = (admin: AdminCredentials, jobId: string) =>
    this.request<Job>(`/jobs/${encodeURIComponent(jobId)}`, { admin })
  deactivate = (admin: AdminCredentials, documentId: string) =>
    this.request<PublicationResult>(`/documents/${encodeURIComponent(documentId)}/deactivate`, {
      method: 'POST',
      admin,
    })
  reactivate = (admin: AdminCredentials, documentId: string) =>
    this.request<PublicationResult>(`/documents/${encodeURIComponent(documentId)}/reactivate`, {
      method: 'POST',
      admin,
    })
  reindexDocument = (admin: AdminCredentials, documentId: string) =>
    this.request<ReindexProgress>(`/documents/${encodeURIComponent(documentId)}/reindex`, {
      method: 'POST',
      admin,
    })
  reindexAll = (admin: AdminCredentials) =>
    this.request<ReindexProgress>('/admin/reindex', {
      method: 'POST',
      body: { explicitly_requested: true },
      admin,
    })
  reindexProgress = (admin: AdminCredentials, requestId: string) =>
    this.request<ReindexProgress>(`/admin/reindex/${encodeURIComponent(requestId)}`, { admin })
  requestConfirmation = (
    admin: AdminCredentials,
    resourceId: string,
    operation: string,
    resourceVersion: string,
  ) =>
    this.request<Confirmation>('/admin/confirmations', {
      method: 'POST',
      body: { resource_id: resourceId, operation, resource_version: resourceVersion },
      admin,
    })
  deleteDocument = (
    admin: AdminCredentials,
    documentId: string,
    confirmationToken: string,
    resourceVersion: string,
  ) =>
    this.request<PublicationResult>(`/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
      body: { confirmation_token: confirmationToken, resource_version: resourceVersion },
      admin,
    })
  diagnostics = (admin: AdminCredentials) => this.request<HealthReport>('/admin/health', { admin })
  metrics = (admin: AdminCredentials) => this.request<OperationalMetrics>('/admin/metrics', { admin })
}
