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
  trace_id?: string | null
  discrepancy?: boolean
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

export interface RecentTraceMetrics {
  window_hours: number
  query_states: Record<string, number>
  abstention_rate: number | null
  latency_ms: { count: number; p50: number | null; p95: number | null }
  cache: { hits: number; misses: number }
  generation_calls: number
  ingestion: {
    jobs_completed: number
    jobs_failed: number
    pages: number
    ocr_pages: number
    fragments: number
    pages_per_minute: number | null
  }
  errors: Record<string, number>
  /** Mandatory AI-layer aggregates (guardrails, caches, router, agent, BreedMatch). */
  layers?: LayerMetrics
}

export interface LayerMetrics {
  latency_ms: Record<string, { count: number; p50: number | null; p95: number | null }>
  guardrails: Record<string, number>
  cache: Record<string, Record<string, number>>
  routes: Record<string, number>
  route_reasons: Record<string, number>
  resolved_models: Record<string, number>
  fallback_used: number
  agent_iterations: Record<string, number>
  breed_match_states: Record<string, number>
  breed_match_feedback: Array<{ route: string | null; model: string | null; useful: number; not_useful: number }>
}

export interface OperationalMetrics {
  generated_at: string
  queries: Record<string, number>
  documents: Record<string, number>
  jobs: Record<string, number>
  feedback: Record<string, number>
  recent?: RecentTraceMetrics
  model_availability?: { status: ComponentState; detail: string }
}

export interface AdminCredentials {
  secret: string
  actor: string
}

// K9 BreedMatch: structured, cited breed comparison (POST /breed-analyses).

export type CriterionKey = 'hunting_function' | 'size' | 'morphology' | 'coat' | 'work_aptitude'

export type AnalysisStatus = 'completed' | 'partial' | 'abstained' | 'rejected' | 'unavailable'

export type FindingOutcome = 'match' | 'mismatch' | 'not_documented'

export interface BreedCriterion {
  key: CriterionKey
  value: string
  weight: number
}

export interface BreedAnalysisRequest {
  schema_version?: string
  criteria: BreedCriterion[]
  candidate_breeds: string[]
  document_ids: string[]
}

export interface AnalysisCitation {
  id: string | null
  fragment_id: string
  document_id: string
  version_id: string
  title: string
  physical_page: number
  printed_page_label: string | null
}

export interface BreedFinding {
  criterion_key: CriterionKey
  criterion_value: string
  outcome: FindingOutcome
  explanation: string
  citations: AnalysisCitation[]
}

export interface BreedCandidate {
  breed: string
  /** Matched weight / documented weight; null when coverage is below the policy minimum. */
  score: number | null
  documented_weight: number
  possible_weight: number
  coverage: number
  findings: BreedFinding[]
}

export interface AnalysisExecution {
  route: string | null
  resolved_model: string | null
  cache_hit: 'miss' | 'exact' | 'semantic'
  agent_iterations: number
  latency_ms: number | null
  route_reason: string | null
  cache_similarity: number | null
  fallback_used: boolean
  /** "allow" or "action:reason" per guardrail stage that ran. */
  input_guardrail: string | null
  output_guardrail: string | null
}

export interface BreedAnalysisResponse {
  schema_version: string
  analysis_id: string
  status: AnalysisStatus
  snapshot_id: string | null
  criteria: BreedCriterion[]
  candidates: BreedCandidate[]
  limitations: string[]
  trace_id: string | null
  reason: string | null
  execution: AnalysisExecution
  summary: string | null
}

export interface AnalysisFeedback {
  id: string
  analysis_id: string
  trace_id: string
  useful: number
  comment: string | null
  created_at: string
}

/** Logical model aliases and policy versions; never runtime addresses. */
export interface ModelConfiguration {
  text_models: Record<string, string>
  embedding_model: string
  router_policy: string
  guardrail_policy: string
  breed_match_policy: string
  semantic_cache_threshold: number
  agent_max_iterations: number
  breed_match_minimum_coverage: number
}

export interface BreedProfileSection {
  heading: string
  text: string
  citation: AnalysisCitation
}

/** Breed sheet taken from the active corpus: book text per section and its captioned photo. */
export interface BreedProfile {
  breed: string
  sections: BreedProfileSection[]
  photo_url: string | null
  photo_caption: string | null
  photo_page: number | null
}
