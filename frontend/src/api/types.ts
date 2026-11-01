// Contracts mirrored from the versioned backend API (/api/v1). Keep in sync with
// backend/src/k9_expert/presentation/api.py.

export type QueryStatus = 'grounded' | 'abstained' | 'rejected' | 'unverified' | 'unavailable'

export type DocumentStatus = 'candidate' | 'active' | 'deactivated' | 'deleted' | 'error'

export type SourceStatus = DocumentStatus | 'withdrawn'

export type JobStage =
  | 'received'
  | 'validating'
  | 'extracting'
  | 'ocr'
  | 'chunking'
  | 'embedding'
  | 'building_index'
  | 'validating_index'
  | 'publishing'
  | 'available'
  | 'error'

export interface ErrorEnvelope {
  code: string
  message: string
  details: unknown
  trace_id: string
  retryable: boolean
}

export interface QueryFilters {
  document_ids: string[]
  categories: string[]
  breeds: string[]
  sections: string[]
}

export interface QueryRequest {
  text: string
  conversation_id?: string | null
  filters: QueryFilters
}

/** A citation as returned with a fresh answer or stored with a historical one. */
export interface CitationSummary {
  id: string | null
  fragment_id: string | null
  title: string
  author: string | null
  edition: string | null
  physical_page: number
  printed_page_label: string | null
  /** Source state recorded when the answer was produced. */
  source_status: SourceStatus
  /** Source state now; only present on historical answers. */
  current_source_status?: SourceStatus
  document_id?: string
  version_id?: string
}

export interface QueryResponse {
  query_id: string
  answer_id: string | null
  status: QueryStatus
  answer: string
  snapshot_id: string | null
  reason: string | null
  citations: CitationSummary[]
  conversation_id: string | null
}

export interface ConversationSummary {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  query_id: string
  question: string | null
  snapshot_id: string | null
  status: QueryStatus
  created_at: string
  answer_id: string
  answer: string
  citations: CitationSummary[]
}

export interface Conversation {
  id: string
  created_at: string
  updated_at: string
  messages: ConversationMessage[]
}

export interface CitationDetail {
  id: string
  answer_id: string
  fragment_id: string | null
  title: string
  author: string | null
  edition: string | null
  physical_page: number
  printed_page_label: string | null
  excerpt: string | null
  current_excerpt: string | null
  snapshot_id: string | null
  version_id: string | null
  document_id: string | null
  page_start: number | null
  page_end: number | null
  source_status: SourceStatus
  snapshot_valid: boolean
}

export interface PageEvidence {
  id: string
  version_id: string
  physical_page: number
  printed_page_label: string | null
  extracted_text: string | null
  extraction_method: string
}

export interface Feedback {
  id: string
  answer_id: string
  useful: number
  comment: string | null
  created_at: string
}

export interface DocumentSummary {
  id: string
  title: string
  author: string | null
  category: string | null
  status: DocumentStatus
  active_version_id: string | null
  edition: string | null
  /** Resource version used to bind destructive confirmations. */
  updated_at: string
}

export interface DocumentVersion {
  id: string
  content_hash: string
  source_filename: string
  edition: string | null
  status: string
  created_at: string
  job_id: string | null
  job_stage: JobStage | null
  job_attempt: number | null
  failed_stage: string | null
  error_code: string | null
  job_updated_at: string | null
}

export interface UploadResult {
  document_id: string
  version_id: string
  job_id: string
  status: string
}

export interface Job {
  id: string
  version_id: string
  stage: JobStage
  attempt: number
  error_code: string | null
}

export interface ReindexProgress {
  request_id: string
  scope: 'document' | 'complete'
  document_id: string | null
  state: 'queued' | 'running' | 'completed' | 'failed'
  total: number
  completed: number
  failed: number
  jobs: Array<{ id: string; version_id: string; stage: JobStage; attempt: number; error_code: string | null }>
}

export interface Confirmation {
  token: string
  expires_at: string
}

export interface PublicationResult {
  document_id: string
  snapshot_id: string
  status: string
}

export type ComponentState = 'ok' | 'degraded' | 'unavailable'

export interface HealthReport {
  status: ComponentState
  checked_at: string
  components: Record<string, { status: ComponentState; detail: string }>
}

export interface PublicHealth {
  status: string
  worker_concurrency: number
}

export interface OperationalMetrics {
  generated_at: string
  queries: Record<string, number>
  documents: Record<string, number>
  jobs: Record<string, number>
  feedback: Record<string, number>
}

export interface AdminCredentials {
  secret: string
  actor: string
}
