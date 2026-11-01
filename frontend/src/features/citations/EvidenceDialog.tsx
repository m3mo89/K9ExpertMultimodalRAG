import { useCallback, useState } from 'react'
import { useApi } from '../../api/hooks'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Modal } from '../../components/Modal'
import { StatusBadge } from '../../components/StatusBadge'
import { useAsync } from '../../hooks'
import { pageLabel, sourceStatusLabels } from '../../labels'

interface Props {
  citationId: string
  onClose: () => void
}

/** Opens the cited fragment in context and lets the reader walk the cited page range. */
export function EvidenceDialog({ citationId, onClose }: Props) {
  const api = useApi()
  const loadCitation = useCallback(() => api.citation(citationId), [api, citationId])
  const citation = useAsync(loadCitation)
  const detail = citation.data
  const [page, setPage] = useState<number | null>(null)
  const available = detail !== null && detail.version_id !== null && detail.source_status !== 'deleted'
  const shownPage = page ?? detail?.physical_page ?? null
  const loadPage = useCallback(
    () => api.citationPage(citationId, shownPage as number),
    [api, citationId, shownPage],
  )
  const pageView = useAsync(available && shownPage !== null ? loadPage : null)

  return (
    <Modal title="Evidencia citada" onClose={onClose}>
      {citation.loading && <p aria-live="polite">Cargando evidencia…</p>}
      {citation.error !== null && <ErrorNotice error={citation.error} onRetry={citation.reload} />}
      {detail && (
        <>
          <dl className="definition-grid">
            <dt>Documento</dt>
            <dd>
              <cite>{detail.title}</cite>
            </dd>
            <dt>Autor</dt>
            <dd>{detail.author ?? 'No consta'}</dd>
            <dt>Edición</dt>
            <dd>{detail.edition ?? 'No consta'}</dd>
            <dt>Página</dt>
            <dd>{pageLabel(detail.physical_page, detail.printed_page_label)}</dd>
            <dt>Estado actual</dt>
            <dd>
              <StatusBadge tone={detail.source_status === 'active' ? 'ok' : 'warn'}>
                {sourceStatusLabels[detail.source_status]}
              </StatusBadge>
            </dd>
          </dl>
          {!detail.snapshot_valid && (
            <p className="notice notice-warn">
              El fragmento no pertenece al snapshot con el que se respondió; trate esta evidencia
              con cautela.
            </p>
          )}
          <section aria-label="Fragmento citado">
            <h3 className="section-label">Fragmento</h3>
            <blockquote className="evidence">
              {detail.current_excerpt ?? detail.excerpt ?? 'No se conservó un extracto de esta fuente.'}
            </blockquote>
          </section>
          {!available && (
            <p className="notice notice-warn">
              La fuente fue retirada de la biblioteca. Se muestra la referencia bibliográfica
              conservada con la respuesta original.
            </p>
          )}
          {available && detail.page_start !== null && detail.page_end !== null && shownPage !== null && (
            <section aria-label="Página del PDF">
              <div className="page-nav">
                <h3 className="section-label">Página {shownPage} del PDF</h3>
                {detail.page_end > detail.page_start && (
                  <div className="button-row">
                    <button
                      type="button"
                      className="button-secondary"
                      disabled={shownPage <= detail.page_start}
                      onClick={() => setPage(shownPage - 1)}
                    >
                      Página anterior
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      disabled={shownPage >= detail.page_end}
                      onClick={() => setPage(shownPage + 1)}
                    >
                      Página siguiente
                    </button>
                  </div>
                )}
              </div>
              {pageView.loading && <p aria-live="polite">Cargando página…</p>}
              {pageView.error !== null && <ErrorNotice error={pageView.error} onRetry={pageView.reload} />}
              {pageView.data && (
                <pre className="page-text">{pageView.data.extracted_text ?? '(Página sin texto extraído)'}</pre>
              )}
            </section>
          )}
        </>
      )}
    </Modal>
  )
}
