import { useId, useState, type FormEvent } from 'react'
import { useApi } from '../../api/hooks'
import { ErrorNotice } from '../../components/ErrorNotice'

export const COMMENT_LIMIT = 1000

/** Rates a chat answer or, with `analysisId`, a stored BreedMatch report. */
export function FeedbackControls({ answerId, analysisId }: { answerId?: string; analysisId?: string }) {
  const api = useApi()
  const commentId = useId()
  const [useful, setUseful] = useState<boolean | null>(null)
  const [comment, setComment] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [error, setError] = useState<unknown>(null)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (useful === null) return
    setState('sending')
    setError(null)
    try {
      const text = comment.trim() || null
      if (analysisId) await api.submitAnalysisFeedback(analysisId, useful, text)
      else if (answerId) await api.submitFeedback(answerId, useful, text)
      setState('sent')
    } catch (reason) {
      setError(reason)
      setState('idle')
    }
  }

  if (state === 'sent') {
    return (
      <p className="feedback-done" role="status">
        Gracias, su valoración quedó registrada.
      </p>
    )
  }

  return (
    <form className="feedback" onSubmit={submit} aria-label={analysisId ? 'Valorar análisis' : 'Valorar respuesta'}>
      <fieldset>
        <legend className="section-label">¿Le resultó útil?</legend>
        <div className="button-row">
          <button
            type="button"
            className="button-toggle"
            aria-pressed={useful === true}
            onClick={() => setUseful(true)}
          >
            Útil
          </button>
          <button
            type="button"
            className="button-toggle"
            aria-pressed={useful === false}
            onClick={() => setUseful(false)}
          >
            No útil
          </button>
        </div>
      </fieldset>
      {useful !== null && (
        <>
          <label htmlFor={commentId} className="small">
            Comentario opcional ({comment.length}/{COMMENT_LIMIT})
          </label>
          <textarea
            id={commentId}
            value={comment}
            maxLength={COMMENT_LIMIT}
            rows={2}
            onChange={(event) => setComment(event.target.value)}
          />
          <button type="submit" className="button-primary" disabled={state === 'sending'}>
            {state === 'sending' ? 'Enviando…' : 'Enviar valoración'}
          </button>
        </>
      )}
      {error !== null && <ErrorNotice error={error} />}
    </form>
  )
}
