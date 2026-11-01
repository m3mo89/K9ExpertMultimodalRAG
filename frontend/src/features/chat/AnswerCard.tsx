import type { CitationSummary, QueryStatus } from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { queryStatusLabels, reasonMessage } from '../../labels'
import { CitationList } from '../citations/CitationList'
import { FeedbackControls } from './FeedbackControls'

export interface AnswerView {
  status: QueryStatus
  answer: string
  reason: string | null
  answerId: string | null
  citations: CitationSummary[]
}

interface Props {
  pending: boolean
  result: AnswerView | null
  error: unknown
  onRetry: () => void
}

const notices: Partial<Record<QueryStatus, string>> = {
  abstained:
    'No se encontró respaldo documental suficiente en la biblioteca activa. K9 Expert no inventa una respuesta en estos casos.',
  rejected: 'La consulta no cumple las reglas de entrada.',
  unverified:
    'El modelo produjo una respuesta cuyas afirmaciones no pudieron vincularse a la evidencia recuperada, por lo que no se muestra.',
  unavailable: 'El servicio de consulta no está disponible en este momento.',
}

/** Renders one typed query result: a documentary synthesis with sources, or a system notice. */
export function AnswerCard({ pending, result, error, onRetry }: Props) {
  if (pending) {
    return (
      <article className="answer answer-pending" aria-busy="true">
        <p>Consultando la biblioteca…</p>
      </article>
    )
  }
  if (error !== null) {
    return (
      <article className="answer">
        <ErrorNotice error={error} onRetry={onRetry} />
      </article>
    )
  }
  if (!result) return null
  if (result.status === 'grounded') {
    return (
      <article className="answer answer-grounded" aria-label={queryStatusLabels.grounded}>
        <p className="section-label">Síntesis documental</p>
        <div className="answer-text">{result.answer}</div>
        <CitationList citations={result.citations} />
        {result.answerId && <FeedbackControls answerId={result.answerId} />}
      </article>
    )
  }
  const detail = reasonMessage(result.reason)
  return (
    <article className={`answer answer-notice answer-${result.status}`}>
      <p className="section-label">Aviso del sistema · {queryStatusLabels[result.status]}</p>
      <p>{notices[result.status]}</p>
      {detail && <p className="muted">{detail}</p>}
      {result.status === 'unavailable' && (
        <button type="button" className="button-secondary" onClick={onRetry}>
          Reintentar
        </button>
      )}
      {result.answerId && result.status === 'abstained' && (
        <FeedbackControls answerId={result.answerId} />
      )}
    </article>
  )
}
