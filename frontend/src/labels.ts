import { ApiError } from './api/client'
import type { ComponentState, JobStage, QueryStatus, SourceStatus } from './api/types'

export const queryStatusLabels: Record<QueryStatus, string> = {
  grounded: 'Respuesta fundamentada',
  abstained: 'Sin respaldo suficiente',
  rejected: 'Consulta rechazada',
  unverified: 'Respuesta no verificable',
  unavailable: 'Servicio no disponible',
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
