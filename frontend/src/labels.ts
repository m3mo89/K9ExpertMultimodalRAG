import { ApiError } from './api/client'
import type {
  AnalysisStatus,
  ComponentState,
  CriterionKey,
  FindingOutcome,
  JobStage,
  QueryStatus,
  SourceStatus,
} from './api/types'

export const queryStatusLabels: Record<QueryStatus, string> = {
  grounded: 'Respuesta fundamentada',
  abstained: 'Sin respaldo suficiente',
  rejected: 'Consulta rechazada',
  unverified: 'Respuesta no verificable',
  unavailable: 'Servicio no disponible',
}

export const analysisStatusLabels: Record<AnalysisStatus, string> = {
  completed: 'Análisis completo',
  partial: 'Análisis parcial',
  abstained: 'Sin evidencia suficiente',
  rejected: 'Criterios rechazados',
  unavailable: 'Servicio no disponible',
}

export const findingOutcomeLabels: Record<FindingOutcome, string> = {
  match: 'Coincide',
  mismatch: 'No coincide',
  not_documented: 'No documentado',
}

export const criterionLabels: Record<CriterionKey, string> = {
  hunting_function: 'Función de caza',
  size: 'Tamaño',
  morphology: 'Morfología',
  coat: 'Manto',
  work_aptitude: 'Aptitud de trabajo',
}

export const cacheLabels: Record<string, string> = {
  miss: 'Sin caché',
  exact: 'Caché exacta',
  semantic: 'Caché semántica',
}

export const sourceStatusLabels: Record<SourceStatus, string> = {
  candidate: 'En proceso',
  active: 'Activa',
  deactivated: 'Desactivada',
  deleted: 'Eliminada',
  error: 'Con error',
  withdrawn: 'Retirada',
}

export const jobStageLabels: Record<JobStage, string> = {
  received: 'Recibido',
  validating: 'Validando',
  extracting: 'Extrayendo texto',
  ocr: 'Aplicando OCR',
  chunking: 'Fragmentando',
  embedding: 'Generando embeddings',
  building_index: 'Construyendo índice',
  validating_index: 'Validando índice',
  publishing: 'Publicando',
  available: 'Disponible',
  error: 'Error',
}

export const componentStateLabels: Record<ComponentState, string> = {
  ok: 'Operativo',
  degraded: 'Degradado',
  unavailable: 'No disponible',
}

export const componentLabels: Record<string, string> = {
  api: 'API',
  database: 'Base de datos',
  worker: 'Trabajador de ingesta',
  storage: 'Almacenamiento',
  active_snapshot: 'Snapshot activo',
  vector_index: 'Índice vectorial',
  inference: 'Modelos locales',
  queries: 'Consultas',
}

const errorMessages: Record<string, string> = {
  network_unavailable: 'No se pudo contactar con el servidor local.',
  unexpected_response: 'El servidor devolvió una respuesta inesperada.',
  internal_error: 'El servidor no pudo completar la solicitud. Inténtelo de nuevo.',
  request_validation_failed: 'La solicitud no es válida.',
  admin_unauthorized: 'Credencial administrativa no válida.',
  conversation_not_found: 'La conversación no existe.',
  citation_not_found: 'La cita no existe.',
  page_not_found: 'La página ya no está disponible.',
  page_outside_citation_range: 'La página está fuera del rango citado.',
  feedback_comment_too_long: 'El comentario supera la longitud permitida.',
  answer_not_found: 'La respuesta no existe.',
  invalid_pdf_filename: 'El archivo debe tener extensión .pdf.',
  invalid_pdf_signature: 'El archivo no es un PDF válido.',
  invalid_pdf_integrity: 'El PDF está dañado.',
  encrypted_pdf: 'El PDF está cifrado.',
  invalid_pdf_page_count: 'El PDF supera el número de páginas permitido.',
  upload_too_large: 'El archivo supera el tamaño permitido.',
  stale_resource_version: 'El documento cambió; solicite una nueva confirmación.',
  invalid_confirmation: 'La confirmación caducó o no es válida.',
  document_has_no_version: 'El documento no tiene versión para reindexar.',
}

const reasonMessages: Record<string, string> = {
  invalid_query: 'La pregunta está vacía o supera la longitud permitida.',
  no_active_snapshot: 'Todavía no hay una biblioteca publicada para consultar.',
  out_of_domain: 'La pregunta está fuera del ámbito cinológico de la biblioteca.',
  no_evidence: 'No se encontró respaldo documental suficiente en las fuentes seleccionadas.',
  weak_evidence: 'La evidencia encontrada es demasiado débil para responder con seguridad.',
  restore_in_progress: 'Hay una restauración en curso; las consultas están en pausa.',
  restore_sources_missing: 'Faltan archivos fuente tras la restauración.',
  index_rebuild_required: 'El índice debe reconstruirse antes de volver a consultar.',
  model_abstained: 'Las fuentes recuperadas no responden directamente a la pregunta.',
  invalid_citations: 'La respuesta generada no pudo verificarse contra la evidencia.',
  model_output_invalid: 'El modelo devolvió una respuesta no verificable.',
  model_unavailable: 'El modelo local no está disponible. Inténtelo de nuevo.',
  input_bounds_invalid: 'Los criterios están vacíos o superan la longitud permitida.',
  prompt_injection_detected: 'Los criterios contienen instrucciones no permitidas.',
  sensitive_data_detected: 'Los criterios contienen datos personales; elimínelos.',
  criteria_required: 'Indique al menos un criterio.',
  criterion_not_supported: 'Uno de los criterios no está admitido.',
  criterion_invalid: 'Uno de los criterios no es válido.',
  no_candidates: 'La biblioteca activa no documenta razas candidatas.',
  citation_not_allowed: 'Un hallazgo cita evidencia no verificable.',
  citation_required: 'Un hallazgo carece de cita.',
}

export function reasonMessage(reason: string | null): string | null {
  if (!reason) return null
  return reasonMessages[reason] ?? reason
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code.startsWith('duplicate:')) return 'Ya existe una versión con el mismo contenido.'
    return errorMessages[error.code] ?? `Error: ${error.code}`
  }
  return 'Se produjo un error inesperado.'
}

export function pageLabel(physicalPage: number, printedLabel: string | null): string {
  return printedLabel && printedLabel !== String(physicalPage)
    ? `pág. ${printedLabel} (PDF ${physicalPage})`
    : `pág. ${physicalPage}`
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' })
}
