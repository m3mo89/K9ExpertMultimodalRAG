import { useState } from 'react'
import type { CitationSummary, SourceStatus } from '../../api/types'
import { StatusBadge } from '../../components/StatusBadge'
import { pageLabel, sourceStatusLabels } from '../../labels'
import { EvidenceDialog } from './EvidenceDialog'

function sourceTone(status: SourceStatus): 'ok' | 'warn' | 'error' {
  if (status === 'active') return 'ok'
  return status === 'deleted' || status === 'withdrawn' ? 'error' : 'warn'
}

export function CitationItem({ citation, index }: { citation: CitationSummary; index: number }) {
  const [open, setOpen] = useState(false)
  // Historical answers carry the current state; fresh answers were cited from active sources.
  const current = citation.current_source_status ?? citation.source_status
  const withdrawn = current !== 'active'
  const bibliographic = [citation.author, citation.edition && `${citation.edition}.ª ed.`]
    .filter(Boolean)
    .join(' · ')
  return (
    <li className="citation">
      <span className="citation-index" aria-hidden="true">
        {index + 1}
      </span>
      <div className="citation-body">
        <p className="citation-title">
          <cite>{citation.title}</cite>
          {bibliographic && <span className="muted"> — {bibliographic}</span>}
        </p>
        <p className="citation-meta">
          <span>{pageLabel(citation.physical_page, citation.printed_page_label)}</span>
          <StatusBadge tone={sourceTone(current)}>{sourceStatusLabels[current]}</StatusBadge>
          {withdrawn && (
            <span className="muted small">Se conserva la cita tal como se produjo.</span>
          )}
        </p>
      </div>
      <button
        type="button"
        className="button-secondary"
        disabled={!citation.id}
        onClick={() => setOpen(true)}
        aria-label={`Ver evidencia de la cita ${index + 1}: ${citation.title}, ${pageLabel(
          citation.physical_page,
          citation.printed_page_label,
        )}`}
      >
        Ver evidencia
      </button>
      {open && citation.id && (
        <EvidenceDialog citationId={citation.id} onClose={() => setOpen(false)} />
      )}
    </li>
  )
}

export function CitationList({ citations }: { citations: CitationSummary[] }) {
  if (citations.length === 0) return null
  return (
    <section className="citations" aria-label="Fuentes citadas">
      <h3 className="section-label">Fuentes</h3>
      <ol className="citation-list">
        {citations.map((citation, index) => (
          <CitationItem
            key={citation.id ?? `${citation.fragment_id}-${index}`}
            citation={citation}
            index={index}
          />
        ))}
      </ol>
    </section>
  )
}
