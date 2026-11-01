import { useCallback, useId, useState, type FormEvent } from 'react'
import { useAdmin, useApi } from '../../api/hooks'
import type { AdminCredentials, DocumentSummary, Job, ReindexProgress } from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Modal } from '../../components/Modal'
import { useAsync, usePolling } from '../../hooks'
import { formatDate, jobStageLabels } from '../../labels'
import { DocumentCard } from '../library/LibraryView'

export function AdminLogin() {
  const api = useApi()
  const { setCredentials } = useAdmin()
  const secretId = useId()
  const actorId = useId()
  const [secret, setSecret] = useState('')
  const [actor, setActor] = useState('local-admin')
  const [error, setError] = useState<unknown>(null)
  const [checking, setChecking] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const candidate = { secret, actor: actor.trim() || 'local-admin' }
    setChecking(true)
    setError(null)
    try {
      await api.diagnostics(candidate)
      setCredentials(candidate)
    } catch (reason) {
      setError(reason)
    } finally {
      setChecking(false)
    }
  }

  return (
    <form className="card narrow" onSubmit={submit} aria-labelledby="admin-login-heading">
      <h2 id="admin-login-heading">Acceso administrativo</h2>
      <p className="muted small">
        La credencial se conserva solo en memoria mientras la pestaña esté abierta.
      </p>
      <label htmlFor={secretId}>Secreto administrativo</label>
      <input
        id={secretId}
        type="password"
        autoComplete="current-password"
        required
        value={secret}
        onChange={(event) => setSecret(event.target.value)}
      />
      <label htmlFor={actorId}>Identificador del administrador</label>
      <input
        id={actorId}
        type="text"
        maxLength={100}
        value={actor}
        onChange={(event) => setActor(event.target.value)}
      />
      <button type="submit" className="button-primary" disabled={checking || !secret}>
        {checking ? 'Verificando…' : 'Entrar'}
      </button>
      {error !== null && <ErrorNotice error={error} />}
    </form>
  )
}

const pipeline = [
  'received',
  'extracting',
  'chunking',
  'embedding',
  'building_index',
  'validating_index',
  'publishing',
  'available',
] as const

export function JobProgress({ admin, jobId, onDone }: { admin: AdminCredentials; jobId: string; onDone?: () => void }) {
  const api = useApi()
  const tick = useCallback(() => api.job(admin, jobId), [api, admin, jobId])
  const isDone = useCallback(
    (job: Job) => {
      const done = job.stage === 'available' || job.stage === 'error'
      if (done) onDone?.()
      return done
    },
    [onDone],
  )
  const { value: job, error } = usePolling(tick, isDone)
  if (error !== null) return <ErrorNotice error={error} />
  if (!job) return <p className="small muted">Consultando el trabajo…</p>
  const index = pipeline.indexOf(job.stage as (typeof pipeline)[number])
  const percent = job.stage === 'available' ? 100 : Math.max(0, Math.round((index / (pipeline.length - 1)) * 100))
  return (
    <div className="progress-block">
      <p className="small" role="status">
        Trabajo: <strong>{jobStageLabels[job.stage]}</strong>
        {job.attempt > 1 ? ` · intento ${job.attempt}` : ''}
        {job.error_code ? ` · código ${job.error_code}` : ''}
      </p>
      <progress max={100} value={job.stage === 'error' ? undefined : percent} aria-label="Progreso de ingesta">
        {percent}%
      </progress>
    </div>
  )
}

export function ReindexProgressView({
  admin,
  initial,
  onDone,
}: {
  admin: AdminCredentials
  initial: ReindexProgress
  onDone?: () => void
}) {
  const api = useApi()
  const tick = useCallback(() => api.reindexProgress(admin, initial.request_id), [api, admin, initial.request_id])
  const isDone = useCallback(
    (progress: ReindexProgress) => {
      const done = progress.state === 'completed' || progress.state === 'failed'
      if (done) onDone?.()
      return done
    },
    [onDone],
  )
  const { value, error } = usePolling(tick, isDone)
  const progress = value ?? initial
  const labels = { queued: 'En cola', running: 'En curso', completed: 'Completada', failed: 'Con fallos' }
  return (
    <div className="progress-block">
      <p className="small" role="status">
        Reindexación {progress.scope === 'complete' ? 'completa' : 'del documento'}:{' '}
        <strong>{labels[progress.state]}</strong> · {progress.completed}/{progress.total} completados
        {progress.failed > 0 ? ` · ${progress.failed} con error` : ''}
      </p>
      <progress max={Math.max(progress.total, 1)} value={progress.completed + progress.failed} aria-label="Progreso de reindexación" />
      {error !== null && <ErrorNotice error={error} />}
    </div>
  )
}

function UploadForm({ admin, onUploaded }: { admin: AdminCredentials; onUploaded: () => void }) {
  const api = useApi()
  const ids = { file: useId(), title: useId(), author: useId(), category: useId() }
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [category, setCategory] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [sending, setSending] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) return
    const form = event.currentTarget
    setSending(true)
    setError(null)
    try {
      const result = await api.uploadDocument(admin, file, { title, author, category })
      setJobId(result.job_id)
      setTitle('')
      setAuthor('')
      setCategory('')
      setFile(null)
      form.reset()
      onUploaded()
    } catch (reason) {
      setError(reason)
    } finally {
      setSending(false)
    }
  }

  return (
    <form className="card" onSubmit={submit} aria-labelledby="upload-heading">
      <h2 id="upload-heading">Incorporar documento</h2>
      <div className="form-grid">
        <div className="field span-2">
          <label htmlFor={ids.file}>Archivo PDF</label>
          <input
            id={ids.file}
            type="file"
            accept="application/pdf,.pdf"
            aria-required="true"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>
        <div className="field span-2">
          <label htmlFor={ids.title}>Título</label>
          <input id={ids.title} required maxLength={300} value={title} onChange={(event) => setTitle(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={ids.author}>Autor</label>
          <input id={ids.author} maxLength={200} value={author} onChange={(event) => setAuthor(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={ids.category}>Categoría</label>
          <input id={ids.category} maxLength={100} value={category} onChange={(event) => setCategory(event.target.value)} />
        </div>
      </div>
      <button type="submit" className="button-primary" disabled={sending || !file || !title.trim()}>
        {sending ? 'Subiendo…' : 'Subir y procesar'}
      </button>
      {error !== null && <ErrorNotice error={error} />}
      {jobId && <JobProgress admin={admin} jobId={jobId} onDone={onUploaded} />}
    </form>
  )
}

type Operation =
  | { kind: 'job'; jobId: string }
  | { kind: 'reindex'; progress: ReindexProgress }
  | { kind: 'done'; message: string }

function DeleteDialog({
  admin,
  document,
  onClose,
  onDeleted,
}: {
  admin: AdminCredentials
  document: DocumentSummary
  onClose: () => void
  onDeleted: () => void
}) {
  const api = useApi()
  const ackId = useId()
  const load = useCallback(
    () => api.requestConfirmation(admin, document.id, 'delete', document.updated_at),
    [api, admin, document.id, document.updated_at],
  )
  const confirmation = useAsync(load)
  const [acknowledged, setAcknowledged] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [deleting, setDeleting] = useState(false)

  const confirm = async () => {
    if (!confirmation.data) return
    setDeleting(true)
    setError(null)
    try {
      await api.deleteDocument(admin, document.id, confirmation.data.token, document.updated_at)
      onDeleted()
    } catch (reason) {
      setError(reason)
      setDeleting(false)
    }
  }

  return (
    <Modal title={`Eliminar «${document.title}»`} onClose={onClose}>
      <p>
        El documento dejará de usarse en nuevas consultas y sus archivos se eliminarán físicamente
        tras el periodo de retención. Las respuestas históricas conservarán su cita marcada como
        fuente retirada.
      </p>
      {confirmation.loading && <p aria-live="polite">Solicitando confirmación…</p>}
      {confirmation.error !== null && <ErrorNotice error={confirmation.error} onRetry={confirmation.reload} />}
      {confirmation.data && (
        <>
          <p className="small muted">La confirmación caduca {formatDate(confirmation.data.expires_at)}.</p>
          <label className="check">
            <input id={ackId} type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
            Entiendo que esta acción no se puede deshacer desde la interfaz.
          </label>
          <div className="button-row">
            <button type="button" className="button-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="button" className="button-danger" disabled={!acknowledged || deleting} onClick={() => void confirm()}>
              {deleting ? 'Eliminando…' : 'Eliminar documento'}
            </button>
          </div>
        </>
      )}
      {error !== null && <ErrorNotice error={error} onRetry={confirmation.reload} />}
    </Modal>
  )
}

function DocumentActions({
  admin,
  document,
  onChanged,
}: {
  admin: AdminCredentials
  document: DocumentSummary
  onChanged: () => void
}) {
  const api = useApi()
  const replaceId = useId()
  const [operation, setOperation] = useState<Operation | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [replacement, setReplacement] = useState<File | null>(null)

  const perform = async (action: () => Promise<Operation>) => {
    setBusy(true)
    setError(null)
    try {
      setOperation(await action())
      onChanged()
    } catch (reason) {
      setError(reason)
    } finally {
      setBusy(false)
    }
  }

  if (document.status === 'deleted') {
    return <p className="small muted">Documento eliminado; pendiente de limpieza física.</p>
  }

  return (
    <div className="admin-actions">
      <div className="button-row">
        {document.status === 'active' ? (
          <button
            type="button"
            className="button-secondary"
            disabled={busy}
            onClick={() =>
              void perform(async () => {
                await api.deactivate(admin, document.id)
                return { kind: 'done', message: 'Documento desactivado; un nuevo snapshot lo excluye.' }
              })
            }
          >
            Desactivar
          </button>
        ) : (
          <button
            type="button"
            className="button-secondary"
            disabled={busy || !document.active_version_id}
            onClick={() =>
              void perform(async () => {
                await api.reactivate(admin, document.id)
                return { kind: 'done', message: 'Documento activado en un nuevo snapshot.' }
              })
            }
          >
            Activar
          </button>
        )}
        <button
          type="button"
          className="button-secondary"
          disabled={busy}
          onClick={() =>
            void perform(async () => ({ kind: 'reindex', progress: await api.reindexDocument(admin, document.id) }))
          }
        >
          Reindexar
        </button>
        <button type="button" className="button-danger-outline" disabled={busy} onClick={() => setDeleting(true)}>
          Eliminar…
        </button>
      </div>
      <form
        className="replace-row"
        onSubmit={(event) => {
          event.preventDefault()
          if (!replacement) return
          const form = event.currentTarget
          void perform(async () => {
            const result = await api.replaceDocument(admin, document.id, replacement)
            form.reset()
            setReplacement(null)
            return { kind: 'job', jobId: result.job_id }
          })
        }}
      >
        <label htmlFor={replaceId} className="small">
          Reemplazar con nueva versión
        </label>
        <input
          id={replaceId}
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => setReplacement(event.target.files?.[0] ?? null)}
        />
        <button type="submit" className="button-secondary" disabled={busy || !replacement}>
          Subir versión
        </button>
      </form>
      {error !== null && <ErrorNotice error={error} />}
      {operation?.kind === 'done' && (
        <p className="small" role="status">
          {operation.message}
        </p>
      )}
      {operation?.kind === 'job' && <JobProgress admin={admin} jobId={operation.jobId} onDone={onChanged} />}
      {operation?.kind === 'reindex' && (
        <ReindexProgressView admin={admin} initial={operation.progress} onDone={onChanged} />
      )}
      {deleting && (
        <DeleteDialog
          admin={admin}
          document={document}
          onClose={() => setDeleting(false)}
          onDeleted={() => {
            setDeleting(false)
            setOperation({ kind: 'done', message: 'Documento eliminado y retirado de nuevas consultas.' })
            onChanged()
          }}
        />
      )}
    </div>
  )
}

function CompleteReindex({ admin }: { admin: AdminCredentials }) {
  const api = useApi()
  const [confirming, setConfirming] = useState(false)
  const [progress, setProgress] = useState<ReindexProgress | null>(null)
  const [error, setError] = useState<unknown>(null)

  const start = async () => {
    setConfirming(false)
    setError(null)
    try {
      setProgress(await api.reindexAll(admin))
    } catch (reason) {
      setError(reason)
    }
  }

  return (
    <section className="card" aria-labelledby="full-reindex-heading">
      <h2 id="full-reindex-heading">Reindexación completa</h2>
      <p className="muted small">
        Regenera todas las versiones. Solo es necesaria tras un cambio incompatible de embeddings o
        fragmentación; puede tardar y consume recursos del equipo.
      </p>
      <button type="button" className="button-secondary" onClick={() => setConfirming(true)}>
        Solicitar reindexación completa…
      </button>
      {confirming && (
        <Modal title="Confirmar reindexación completa" onClose={() => setConfirming(false)}>
          <p>Se reprocesarán todas las versiones de la biblioteca. Las consultas seguirán usando el snapshot publicado.</p>
          <div className="button-row">
            <button type="button" className="button-secondary" onClick={() => setConfirming(false)}>
              Cancelar
            </button>
            <button type="button" className="button-primary" onClick={() => void start()}>
              Reindexar todo
            </button>
          </div>
        </Modal>
      )}
      {error !== null && <ErrorNotice error={error} />}
      {progress && <ReindexProgressView admin={admin} initial={progress} />}
    </section>
  )
}

export function AdminView() {
  const api = useApi()
  const { credentials, setCredentials } = useAdmin()
  const load = useCallback(() => api.listDocuments(), [api])
  const documents = useAsync(credentials ? load : null)

  return (
    <section className="page" aria-labelledby="admin-heading">
      <header className="page-header">
        <h1 id="admin-heading">Administración</h1>
        {credentials && (
          <p className="muted small">
            Sesión de <strong>{credentials.actor}</strong> ·{' '}
            <button type="button" className="button-link" onClick={() => setCredentials(null)}>
              Cerrar sesión
            </button>
          </p>
        )}
      </header>
      {!credentials ? (
        <AdminLogin />
      ) : (
        <>
          <UploadForm admin={credentials} onUploaded={documents.reload} />
          <h2 className="list-heading">Documentos</h2>
          {documents.error !== null && <ErrorNotice error={documents.error} onRetry={documents.reload} />}
          <ul className="card-list">
            {(documents.data ?? []).map((document) => (
              <DocumentCard
                key={document.id}
                document={document}
                actions={<DocumentActions admin={credentials} document={document} onChanged={documents.reload} />}
              />
            ))}
          </ul>
          {documents.data?.length === 0 && <p className="muted">Todavía no hay documentos.</p>}
          <CompleteReindex admin={credentials} />
        </>
      )}
    </section>
  )
}
