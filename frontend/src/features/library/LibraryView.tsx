import { useCallback, useId, useMemo, useState, type ReactNode } from 'react'
import { useApi } from '../../api/hooks'
import type { DocumentStatus, DocumentSummary, DocumentVersion } from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { StatusBadge } from '../../components/StatusBadge'
import { useAsync } from '../../hooks'
import { formatDate, jobStageLabels, sourceStatusLabels } from '../../labels'

function statusTone(status: DocumentStatus): 'ok' | 'warn' | 'error' | 'neutral' {
  if (status === 'active') return 'ok'
  if (status === 'error' || status === 'deleted') return 'error'
  return status === 'candidate' ? 'neutral' : 'warn'
}

function VersionRow({ version }: { version: DocumentVersion }) {
  const failed = version.job_stage === 'error'
  return (
    <li className="version">
      <div className="version-head">
        <span className="mono small">{version.source_filename}</span>
        <StatusBadge tone={failed ? 'error' : version.status === 'active' ? 'ok' : 'neutral'}>
          {version.status}
        </StatusBadge>
      </div>
      <dl className="definition-grid small">
        <dt>Edición</dt>
        <dd>{version.edition ?? 'No consta'}</dd>
        <dt>Registrada</dt>
        <dd>{formatDate(version.created_at)}</dd>
        <dt>Procesamiento</dt>
        <dd>
          {version.job_stage ? jobStageLabels[version.job_stage] : 'Sin trabajo registrado'}
          {version.job_attempt ? ` · intento ${version.job_attempt}` : ''}
        </dd>
        <dt>Huella</dt>
        <dd className="mono">{version.content_hash.slice(0, 12)}</dd>
      </dl>
      {failed && (
        <div className="notice notice-error">
          <p>
            Falló en la etapa <strong>{version.failed_stage ?? 'desconocida'}</strong> con el código{' '}
            <code>{version.error_code ?? 'sin_codigo'}</code>.
          </p>
          <p className="small">
            {formatDate(version.job_updated_at)} · Reintentable mediante reindexación desde
            Administración.
          </p>
        </div>
      )}
    </li>
  )
}

function VersionHistory({ documentId }: { documentId: string }) {
  const api = useApi()
  const load = useCallback(() => api.listVersions(documentId), [api, documentId])
  const versions = useAsync(load)
  if (versions.loading) return <p className="muted small">Cargando versiones…</p>
  if (versions.error !== null) return <ErrorNotice error={versions.error} onRetry={versions.reload} />
  return (
    <ol className="version-list">
      {(versions.data ?? []).map((version) => (
        <VersionRow key={version.id} version={version} />
      ))}
    </ol>
  )
}

export function DocumentCard({ document, actions }: { document: DocumentSummary; actions?: ReactNode }) {
  const [showVersions, setShowVersions] = useState(false)
  return (
    <li className="card document-card">
      <div className="document-head">
        <h2 className="document-title">{document.title}</h2>
        <StatusBadge tone={statusTone(document.status)}>{sourceStatusLabels[document.status]}</StatusBadge>
      </div>
      <dl className="definition-grid small">
        <dt>Autor</dt>
        <dd>{document.author ?? 'No consta'}</dd>
        <dt>Categoría</dt>
        <dd>{document.category ?? 'Sin categoría'}</dd>
        <dt>Edición</dt>
        <dd>{document.edition ?? 'No consta'}</dd>
        <dt>Disponibilidad</dt>
        <dd>{document.active_version_id ? 'Versión publicada' : 'Sin versión publicada'}</dd>
      </dl>
      {actions}
      <details className="versions" onToggle={(event) => setShowVersions(event.currentTarget.open)}>
        <summary>Historial de versiones</summary>
        {showVersions && <VersionHistory documentId={document.id} />}
      </details>
    </li>
  )
}

type StatusFilter = 'active' | 'all' | DocumentStatus

export function LibraryView() {
  const api = useApi()
  const searchId = useId()
  const categoryId = useId()
  const statusId = useId()
  const load = useCallback(() => api.listDocuments(), [api])
  const documents = useAsync(load)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState<StatusFilter>('active')

  const categories = useMemo(
    () => [...new Set((documents.data ?? []).map((item) => item.category).filter(Boolean))] as string[],
    [documents.data],
  )
  const visible = (documents.data ?? []).filter((item) => {
    const term = search.trim().toLowerCase()
    const matchesText =
      !term || [item.title, item.author ?? ''].some((value) => value.toLowerCase().includes(term))
    const matchesStatus = status === 'all' || item.status === status
    return matchesText && matchesStatus && (!category || item.category === category)
  })

  return (
    <section className="page" aria-labelledby="library-heading">
      <header className="page-header">
        <h1 id="library-heading">Biblioteca de conocimiento</h1>
        <p className="muted">Fuentes documentales, su estado y su historial de versiones.</p>
      </header>
      <div className="toolbar" role="search">
        <div className="field">
          <label htmlFor={searchId}>Buscar</label>
          <input
            id={searchId}
            type="search"
            value={search}
            placeholder="Título o autor"
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor={categoryId}>Categoría</label>
          <select id={categoryId} value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Todas</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={statusId}>Estado</label>
          <select
            id={statusId}
            value={status}
            onChange={(event) => setStatus(event.target.value as StatusFilter)}
          >
            <option value="active">Activas</option>
            <option value="all">Todas</option>
            <option value="candidate">En proceso</option>
            <option value="deactivated">Desactivadas</option>
            <option value="error">Con error</option>
            <option value="deleted">Eliminadas</option>
          </select>
        </div>
      </div>
      {documents.loading && <p aria-live="polite">Cargando biblioteca…</p>}
      {documents.error !== null && <ErrorNotice error={documents.error} onRetry={documents.reload} />}
      {documents.data && visible.length === 0 && (
        <p className="empty-state muted">No hay documentos que coincidan con los filtros.</p>
      )}
      <ul className="card-list">
        {visible.map((item) => (
          <DocumentCard key={item.id} document={item} />
        ))}
      </ul>
    </section>
  )
}
