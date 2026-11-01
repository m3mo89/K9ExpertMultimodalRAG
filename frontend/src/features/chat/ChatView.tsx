import { useCallback, useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useApi } from '../../api/hooks'
import type { ConversationMessage, QueryFilters, QueryResponse } from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { useAsync } from '../../hooks'
import { errorMessage, formatDate, queryStatusLabels } from '../../labels'
import { AnswerCard, type AnswerView } from './AnswerCard'
import { FilterPanel } from './FilterPanel'
import { emptyFilters, filterCount } from './filters'

export const QUESTION_LIMIT = 2000

interface Exchange {
  key: string
  question: string
  filters: QueryFilters
  pending: boolean
  result: AnswerView | null
  error: unknown
}

function fromResponse(response: QueryResponse): AnswerView {
  return {
    status: response.status,
    answer: response.answer,
    reason: response.reason,
    answerId: response.answer_id,
    citations: response.citations,
    discrepancy: response.discrepancy ?? false,
  }
}

function fromHistory(message: ConversationMessage): Exchange {
  return {
    key: message.query_id,
    question: message.question ?? '(pregunta no conservada)',
    filters: emptyFilters,
    pending: false,
    error: null,
    result: {
      status: message.status,
      answer: message.answer,
      reason: null,
      answerId: message.answer_id,
      citations: message.citations,
    },
  }
}

export function ChatView() {
  const api = useApi()
  const questionId = useId()
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [question, setQuestion] = useState('')
  const [filters, setFilters] = useState<QueryFilters>(emptyFilters)
  const [historyError, setHistoryError] = useState<unknown>(null)
  const threadEnd = useRef<HTMLDivElement>(null)
  // History starts collapsed on phone-sized screens so the thread stays in view.
  const [historyOpen] = useState(() => window.matchMedia?.('(min-width: 761px)').matches ?? true)

  const loadConversations = useCallback(() => api.listConversations(), [api])
  const conversations = useAsync(loadConversations)
  const loadDocuments = useCallback(() => api.listDocuments(), [api])
  const documents = useAsync(loadDocuments)

  useEffect(() => {
    threadEnd.current?.scrollIntoView?.({ block: 'end' })
  }, [exchanges])

  const update = (key: string, patch: Partial<Exchange>) =>
    setExchanges((items) => items.map((item) => (item.key === key ? { ...item, ...patch } : item)))

  const run = async (key: string, text: string, scope: QueryFilters) => {
    update(key, { pending: true, error: null, result: null })
    try {
      let target = conversationId
      if (!target) {
        target = (await api.createConversation()).id
        setConversationId(target)
      }
      const response = await api.submitQuery({ text, conversation_id: target, filters: scope })
      update(key, { pending: false, result: fromResponse(response) })
      conversations.reload()
    } catch (error) {
      update(key, { pending: false, error })
    }
  }

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const text = question.trim()
    if (!text || exchanges.some((item) => item.pending)) return
    const key = crypto.randomUUID()
    setExchanges((items) => [
      ...items,
      { key, question: text, filters, pending: true, result: null, error: null },
    ])
    setQuestion('')
    void run(key, text, filters)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) submit()
  }

  const openConversation = async (id: string) => {
    setHistoryError(null)
    try {
      const conversation = await api.conversation(id)
      setConversationId(conversation.id)
      setExchanges(conversation.messages.map(fromHistory))
    } catch (error) {
      setHistoryError(error)
    }
  }

  const startNew = () => {
    setConversationId(null)
    setExchanges([])
    setHistoryError(null)
  }

  const busy = exchanges.some((item) => item.pending)
  const last = exchanges.at(-1)
  const announcement = !last
    ? ''
    : last.pending
      ? 'Consultando la biblioteca…'
      : last.result
        ? queryStatusLabels[last.result.status]
        : last.error !== null
          ? errorMessage(last.error)
          : ''

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar" aria-label="Conversaciones">
        <button type="button" className="button-primary block" onClick={startNew}>
          Nueva conversación
        </button>
        <details className="history" open={historyOpen}>
          <summary>Historial</summary>
          {conversations.error !== null && (
            <ErrorNotice error={conversations.error} onRetry={conversations.reload} />
          )}
          <ul className="history-list">
            {(conversations.data ?? []).map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="history-item"
                  aria-current={item.id === conversationId ? 'true' : undefined}
                  onClick={() => void openConversation(item.id)}
                >
                  <span className="history-title">{item.title ?? 'Conversación sin preguntas'}</span>
                  <span className="muted small">{formatDate(item.updated_at)}</span>
                </button>
              </li>
            ))}
            {conversations.data?.length === 0 && (
              <li className="muted small">Aún no hay conversaciones.</li>
            )}
          </ul>
        </details>
      </aside>

      <section className="chat-main" aria-labelledby="chat-heading">
        <h1 id="chat-heading" className="visually-hidden">
          Consultar la biblioteca
        </h1>
        {historyError !== null && <ErrorNotice error={historyError} />}
        <p role="status" className="visually-hidden">
          {announcement}
        </p>
        <div className="thread">
          {exchanges.length === 0 && (
            <div className="empty-state">
              <p className="empty-title">Pregunte a la biblioteca cinológica</p>
              <p className="muted">
                Las respuestas se basan solo en las fuentes activas y citan documento, edición y
                página. Si no hay respaldo suficiente, K9 Expert se abstiene.
              </p>
            </div>
          )}
          {exchanges.map((exchange) => (
            <div key={exchange.key} className="exchange">
              <div className="question">
                <p>{exchange.question}</p>
                {filterCount(exchange.filters) > 0 && (
                  <p className="small muted">Ámbito filtrado ({filterCount(exchange.filters)})</p>
                )}
              </div>
              <AnswerCard
                pending={exchange.pending}
                result={exchange.result}
                error={exchange.error}
                onRetry={() => void run(exchange.key, exchange.question, exchange.filters)}
              />
            </div>
          ))}
          <div ref={threadEnd} />
        </div>

        <form className="composer" onSubmit={submit}>
          <FilterPanel documents={documents.data ?? []} filters={filters} onChange={setFilters} />
          <label htmlFor={questionId} className="visually-hidden">
            Pregunta
          </label>
          <div className="composer-row">
            <textarea
              id={questionId}
              value={question}
              maxLength={QUESTION_LIMIT}
              rows={2}
              placeholder="Por ejemplo: ¿qué temperamento describe la enciclopedia para el teckel?"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={onKeyDown}
            />
            <button type="submit" className="button-primary" disabled={busy || !question.trim()}>
              {busy ? 'Consultando…' : 'Preguntar'}
            </button>
          </div>
          <p className="small muted composer-hint">
            {question.length}/{QUESTION_LIMIT} · Intro para enviar, Mayús+Intro para nueva línea
          </p>
        </form>
      </section>
    </div>
  )
}
