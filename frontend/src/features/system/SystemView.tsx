import { useCallback } from 'react'
import { useAdmin, useApi } from '../../api/hooks'
import type { AdminCredentials, ComponentState, OperationalMetrics } from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { StatusBadge } from '../../components/StatusBadge'
import { useAsync } from '../../hooks'
import {
  componentLabels,
  componentStateLabels,
  formatDate,
  jobStageLabels,
  queryStatusLabels,
  sourceStatusLabels,
} from '../../labels'
import { AdminLogin } from '../admin/AdminView'

const tone: Record<ComponentState, 'ok' | 'warn' | 'error'> = {
  ok: 'ok',
  degraded: 'warn',
  unavailable: 'error',
}

const detailLabels: Record<string, string> = {
  worker_never_seen: 'El trabajador de ingesta no se ha iniciado.',
  worker_heartbeat_stale: 'El trabajador no envía señal de vida reciente.',
  low_disk_space: 'Queda poco espacio en disco.',
  storage_not_writable: 'No se puede escribir en el almacenamiento.',
  no_active_snapshot: 'No hay un snapshot publicado; las consultas se abstendrán.',
  index_missing: 'Falta el índice vectorial del snapshot activo.',
  database_unreachable: 'No se puede abrir la base de datos.',
  schema_version_mismatch: 'La versión del esquema no es compatible.',
  database_unavailable: 'No se puede comprobar sin base de datos.',
  inference_unreachable: 'No se puede contactar con el runtime de modelos locales; la biblioteca sigue disponible.',
  model_not_installed: 'Falta un modelo local configurado.',
}

function Diagnostics({ admin }: { admin: AdminCredentials }) {
  const api = useApi()
  const load = useCallback(() => api.diagnostics(admin), [api, admin])
  const report = useAsync(load)
  if (report.error !== null) return <ErrorNotice error={report.error} onRetry={report.reload} />
  if (!report.data) return <p aria-live="polite">Comprobando componentes…</p>
  const { status, checked_at, components } = report.data
  return (
    <section className="card" aria-labelledby="components-heading">
      <div className="card-head">
        <h2 id="components-heading">Componentes</h2>
        <button type="button" className="button-secondary" onClick={report.reload} disabled={report.loading}>
          {report.loading ? 'Comprobando…' : 'Actualizar'}
        </button>
      </div>
      <p className={`notice notice-${status === 'ok' ? 'ok' : status === 'degraded' ? 'warn' : 'error'}`} role="status">
        Estado general: <strong>{componentStateLabels[status]}</strong> · {formatDate(checked_at)}
      </p>
      <ul className="component-grid">
        {Object.entries(components).map(([name, component]) => (
          <li key={name} className={`component component-${component.status}`}>
            <div className="component-head">
              <span>{componentLabels[name] ?? name}</span>
              <StatusBadge tone={tone[component.status]}>{componentStateLabels[component.status]}</StatusBadge>
            </div>
            {component.status !== 'ok' && detailLabels[component.detail] && (
              <p className="small">{detailLabels[component.detail]}</p>
            )}
            <p className="small muted mono">{component.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function CountTable({ caption, counts, labels }: { caption: string; counts: Record<string, number>; labels: Record<string, string> }) {
  const entries = Object.entries(counts)
  const total = entries.reduce((sum, [, count]) => sum + count, 0)
  return (
    <table className="count-table">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th scope="col">Estado</th>
          <th scope="col" className="numeric">Total</th>
          <th scope="col" className="numeric">%</th>
        </tr>
      </thead>
      <tbody>
        {entries.length === 0 && (
          <tr>
            <td colSpan={3} className="muted">Sin datos</td>
          </tr>
        )}
        {entries.map(([key, count]) => (
          <tr key={key}>
            <th scope="row">{labels[key] ?? key}</th>
            <td className="numeric">{count}</td>
            <td className="numeric">{total ? Math.round((count / total) * 100) : 0}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Metrics({ admin }: { admin: AdminCredentials }) {
  const api = useApi()
  const load = useCallback(() => api.metrics(admin), [api, admin])
  const metrics = useAsync<OperationalMetrics>(load)
  if (metrics.error !== null) return <ErrorNotice error={metrics.error} onRetry={metrics.reload} />
  if (!metrics.data) return <p aria-live="polite">Cargando métricas…</p>
  const data = metrics.data
  const answered = Object.values(data.queries).reduce((sum, count) => sum + count, 0)
  const abstained = data.queries.abstained ?? 0
  return (
    <section className="card" aria-labelledby="metrics-heading">
      <div className="card-head">
        <h2 id="metrics-heading">Métricas básicas</h2>
        <span className="small muted">{formatDate(data.generated_at)}</span>
      </div>
      <dl className="stat-row">
        <div className="stat">
          <dt>Consultas registradas</dt>
          <dd>{answered}</dd>
        </div>
        <div className="stat">
          <dt>Tasa de abstención</dt>
          <dd>{answered ? `${Math.round((abstained / answered) * 100)} %` : '—'}</dd>
        </div>
        <div className="stat">
          <dt>Valoraciones útiles</dt>
          <dd>
            {data.feedback.useful ?? 0} / {(data.feedback.useful ?? 0) + (data.feedback.not_useful ?? 0)}
          </dd>
        </div>
      </dl>
      <div className="table-grid">
        <CountTable caption="Consultas por resultado" counts={data.queries} labels={queryStatusLabels} />
        <CountTable caption="Documentos por estado" counts={data.documents} labels={sourceStatusLabels} />
        <CountTable caption="Trabajos de ingesta por etapa" counts={data.jobs} labels={jobStageLabels} />
      </div>
    </section>
  )
}

export function SystemView() {
  const api = useApi()
  const { credentials } = useAdmin()
  const loadHealth = useCallback(() => api.health(), [api])
  const health = useAsync(loadHealth)
  return (
    <section className="page" aria-labelledby="system-heading">
      <header className="page-header">
        <h1 id="system-heading">Sistema</h1>
        <p className="muted" role="status">
          API:{' '}
          {health.error !== null ? (
            <StatusBadge tone="error">No disponible</StatusBadge>
          ) : health.data ? (
            <StatusBadge tone="ok">Operativa</StatusBadge>
          ) : (
            'comprobando…'
          )}
          {health.data && ` · concurrencia del trabajador: ${health.data.worker_concurrency}`}
        </p>
      </header>
      {credentials ? (
        <>
          <Diagnostics admin={credentials} />
          <Metrics admin={credentials} />
        </>
      ) : (
        <>
          <p className="muted">El diagnóstico detallado requiere acceso administrativo.</p>
          <AdminLogin />
        </>
      )}
    </section>
  )
}
