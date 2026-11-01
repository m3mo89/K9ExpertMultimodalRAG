import { ApiError } from '../api/client'
import { errorMessage } from '../labels'

interface Props {
  error: unknown
  onRetry?: () => void
}

/** Shows a safe, localized error; offers retry only when the backend marked it retryable. */
export function ErrorNotice({ error, onRetry }: Props) {
  const retryable = error instanceof ApiError ? error.retryable : true
  const traceId = error instanceof ApiError ? error.traceId : null
  return (
    <div className="notice notice-error" role="alert">
      <p>{errorMessage(error)}</p>
      {traceId && <p className="muted small">Referencia: {traceId}</p>}
      {retryable && onRetry && (
        <button type="button" className="button-secondary" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  )
}
