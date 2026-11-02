import { Fragment, useCallback, useId, useState, type FormEvent } from 'react'
import { useApi } from '../../api/hooks'
import type {
  BreedAnalysisResponse,
  BreedCandidate,
  BreedCriterion,
  CriterionKey,
  FindingOutcome,
} from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { StatusBadge } from '../../components/StatusBadge'
import { useAsync } from '../../hooks'
import {
  analysisStatusLabels,
  cacheLabels,
  criterionLabels,
  findingOutcomeLabels,
  pageLabel,
  reasonMessage,
} from '../../labels'
import { FeedbackControls } from '../chat/FeedbackControls'

export const MAX_CRITERIA = 12

interface CriterionRow extends BreedCriterion {
  id: string
}

const criterionKeys = Object.keys(criterionLabels) as CriterionKey[]

const outcomeTone: Record<FindingOutcome, 'ok' | 'error' | 'neutral'> = {
  match: 'ok',
  mismatch: 'error',
  not_documented: 'neutral',
}

function newRow(key: CriterionKey = 'hunting_function', value = ''): CriterionRow {
  return { id: crypto.randomUUID(), key, value, weight: 1 }
}

function percent(value: number): string {
  return `${Math.round(value * 100)} %`
}

/** Matched weight, recomputed from the analysed criteria so the explanation shows its terms. */
function matchedWeight(candidate: BreedCandidate, criteria: BreedCriterion[]): number {
  const weights = new Map(criteria.map((item) => [`${item.key}:${item.value}`, item.weight]))
  return candidate.findings
    .filter((finding) => finding.outcome === 'match')
    .reduce(
      (sum, finding) => sum + (weights.get(`${finding.criterion_key}:${finding.criterion_value}`) ?? 0),
      0,
    )
}

export function BreedMatchView() {
  const api = useApi()
  const breedsId = useId()
  const [rows, setRows] = useState<CriterionRow[]>(() => [newRow('hunting_function', 'rastro')])
  const [breeds, setBreeds] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [report, setReport] = useState<BreedAnalysisResponse | null>(null)

  const update = (id: string, patch: Partial<CriterionRow>) =>
    setRows((items) => items.map((item) => (item.id === id ? { ...item, ...patch } : item)))

  const usable = rows.filter((item) => item.value.trim())

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (pending || usable.length === 0) return
    setPending(true)
    setError(null)
    try {
      const response = await api.submitBreedAnalysis({
        criteria: usable.map(({ key, value, weight }) => ({ key, value: value.trim(), weight })),
        candidate_breeds: breeds
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        document_ids: [],
      })
      setReport(response)
    } catch (reason) {
      setError(reason)
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="page breedmatch" aria-labelledby="breedmatch-heading">
      <header className="page-header">
        <h1 id="breedmatch-heading">Análisis de razas</h1>
        <p className="muted">
          Indique los criterios de caza que necesita. K9 BreedMatch compara razas con la
          evidencia de la biblioteca y explica cada coincidencia con su cita.
        </p>
      </header>
      <form className="card criteria-form" onSubmit={submit} aria-label="Criterios de análisis">
        <fieldset>
          <legend className="section-label">Criterios</legend>
          <ol className="criteria-list">
            {rows.map((row, index) => (
              <li key={row.id} className="criterion-row">
                <label>
                  <span className="small">Tipo de criterio {index + 1}</span>
                  <select
                    value={row.key}
                    onChange={(event) => update(row.id, { key: event.target.value as CriterionKey })}
                  >
                    {criterionKeys.map((key) => (
                      <option key={key} value={key}>
                        {criterionLabels[key]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="small">Valor del criterio {index + 1}</span>
                  <input
                    type="text"
                    value={row.value}
                    maxLength={200}
                    placeholder="p. ej. rastro, pelo duro, pequeño"
                    onChange={(event) => update(row.id, { value: event.target.value })}
                  />
                </label>
                <label>
                  <span className="small">Peso del criterio {index + 1}</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    step={1}
                    value={row.weight}
                    onChange={(event) =>
                      update(row.id, {
                        weight: Math.min(10, Math.max(1, Number(event.target.value) || 1)),
                      })
                    }
                  />
                </label>
                <button
                  type="button"
                  className="button-ghost"
                  disabled={rows.length === 1}
                  onClick={() => setRows((items) => items.filter((item) => item.id !== row.id))}
                  aria-label={`Quitar criterio ${index + 1}`}
                >
                  Quitar
                </button>
              </li>
            ))}
          </ol>
          <button
            type="button"
            className="button-secondary"
            disabled={rows.length >= MAX_CRITERIA}
            onClick={() => setRows((items) => [...items, newRow('coat')])}
          >
            Añadir criterio
          </button>
        </fieldset>
        <label htmlFor={breedsId} className="small">
          Razas a comparar (opcional, separadas por comas)
        </label>
        <input
          id={breedsId}
          type="text"
          value={breeds}
          placeholder="Si lo deja vacío, se usan las razas documentadas en la biblioteca"
          onChange={(event) => setBreeds(event.target.value)}
        />
        <div className="button-row">
          <button
            type="submit"
            className="button-primary"
            disabled={pending || usable.length === 0}
          >
            {pending ? 'Analizando…' : 'Analizar razas'}
          </button>
        </div>
      </form>
      <div aria-live="polite" className="visually-hidden">
        {pending
          ? 'Analizando la biblioteca…'
          : report
            ? analysisStatusLabels[report.status]
            : ''}
      </div>
      {error !== null && <ErrorNotice error={error} />}
      {report && <AnalysisReport key={report.analysis_id} report={report} />}
      <ModelConfigurationPanel />
    </section>
  )
}

function statusTone(status: BreedAnalysisResponse['status']): 'ok' | 'warn' | 'error' {
  if (status === 'completed') return 'ok'
  return status === 'partial' || status === 'abstained' ? 'warn' : 'error'
}

export function AnalysisReport({ report }: { report: BreedAnalysisResponse }) {
  const reason = report.status === 'completed' ? null : reasonMessage(report.reason)
  return (
    <section className="card analysis-report" aria-label="Informe de análisis">
      <div className="card-head">
        <h2>Informe comparativo</h2>
        <StatusBadge tone={statusTone(report.status)}>
          {analysisStatusLabels[report.status]}
        </StatusBadge>
      </div>
      {reason && <p className="notice notice-warn">{reason}</p>}
      {report.summary && (
        <div className="analysis-summary">
          <h3 className="section-label">Síntesis documental</h3>
          <p>{report.summary}</p>
        </div>
      )}
      {report.candidates.length > 0 && (
        <>
          <ComparisonTable report={report} />
          <ScoreExplanation report={report} />
          <h3 className="section-label">Evidencia por raza</h3>
          {report.candidates.map((candidate) => (
            <CandidateEvidence key={candidate.breed} candidate={candidate} />
          ))}
        </>
      )}
      {report.limitations.length > 0 && (
        <section aria-label="Limitaciones">
          <h3 className="section-label">Limitaciones</h3>
          <ul>
            {report.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}
      <p className="muted small">
        Información documental histórica; no sustituye el consejo de un profesional actual.
      </p>
      <ExecutionDetails report={report} />
      <FeedbackControls analysisId={report.analysis_id} />
    </section>
  )
}

function ComparisonTable({ report }: { report: BreedAnalysisResponse }) {
  return (
    <div className="table-scroll" role="region" aria-label="Tabla comparativa" tabIndex={0}>
      <table className="count-table comparison-table">
        <caption>Comparación por criterio</caption>
        <thead>
          <tr>
            <th scope="col">Raza</th>
            {report.criteria.map((criterion) => (
              <th scope="col" key={`${criterion.key}:${criterion.value}`}>
                {criterionLabels[criterion.key] ?? criterion.key}: {criterion.value}
                <span className="muted"> (peso {criterion.weight})</span>
              </th>
            ))}
            <th scope="col" className="numeric">
              Puntuación
            </th>
            <th scope="col" className="numeric">
              Cobertura
            </th>
          </tr>
        </thead>
        <tbody>
          {report.candidates.map((candidate) => (
            <tr key={candidate.breed}>
              <th scope="row">{candidate.breed}</th>
              {candidate.findings.map((finding) => (
                <td key={`${finding.criterion_key}:${finding.criterion_value}`}>
                  <StatusBadge tone={outcomeTone[finding.outcome]}>
                    {findingOutcomeLabels[finding.outcome]}
                  </StatusBadge>
                </td>
              ))}
              <td className="numeric">
                {candidate.score === null ? 'Sin puntuación' : percent(candidate.score)}
              </td>
              <td className="numeric">{percent(candidate.coverage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ScoreExplanation({ report }: { report: BreedAnalysisResponse }) {
  return (
    <section aria-label="Explicación de la puntuación" className="score-explanation">
      <h3 className="section-label">Cómo se calcula</h3>
      <p className="small">
        Puntuación = peso de los criterios que coinciden ÷ peso de los criterios documentados.
        Los criterios «No documentado» no suman ni restan; reducen la cobertura. Si la cobertura
        no alcanza el mínimo de la política, la raza queda sin puntuación. El modelo de lenguaje
        no interviene en este cálculo.
      </p>
      <ul className="small">
        {report.candidates.map((candidate) => (
          <li key={candidate.breed}>
            <strong>{candidate.breed}</strong>:{' '}
            {candidate.score === null
              ? `sin puntuación; documentado ${candidate.documented_weight} de ${candidate.possible_weight} (${percent(candidate.coverage)}).`
              : `${matchedWeight(candidate, report.criteria)} ÷ ${candidate.documented_weight} = ${percent(candidate.score)}; cobertura ${candidate.documented_weight} de ${candidate.possible_weight}.`}
          </li>
        ))}
      </ul>
    </section>
  )
}

function CandidateEvidence({ candidate }: { candidate: BreedCandidate }) {
  return (
    <details className="candidate-evidence">
      <summary>{candidate.breed}</summary>
      <ul className="finding-list">
        {candidate.findings.map((finding) => (
          <li key={`${finding.criterion_key}:${finding.criterion_value}`} className="finding">
            <p>
              <StatusBadge tone={outcomeTone[finding.outcome]}>
                {findingOutcomeLabels[finding.outcome]}
              </StatusBadge>{' '}
              <strong>
                {criterionLabels[finding.criterion_key] ?? finding.criterion_key}:{' '}
                {finding.criterion_value}
              </strong>
            </p>
            <p className="small">{finding.explanation}</p>
            {finding.citations.length > 0 && (
              <ul className="small citation-refs" aria-label="Citas">
                {finding.citations.map((citation) => (
                  <li key={citation.fragment_id}>
                    <cite>{citation.title}</cite>,{' '}
                    {pageLabel(citation.physical_page, citation.printed_page_label)}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </details>
  )
}

function ExecutionDetails({ report }: { report: BreedAnalysisResponse }) {
  const execution = report.execution
  return (
    <details className="execution-details">
      <summary>Detalles de ejecución</summary>
      <dl className="definition-grid small">
        <dt>Ruta</dt>
        <dd>
          {execution.route ?? '—'}
          {execution.route_reason && ` (${execution.route_reason})`}
        </dd>
        <dt>Modelo</dt>
        <dd>
          {execution.resolved_model ?? '—'}
          {execution.fallback_used && ' · respaldo local'}
        </dd>
        <dt>Caché</dt>
        <dd>
          {cacheLabels[execution.cache_hit] ?? execution.cache_hit}
          {execution.cache_similarity !== null &&
            ` · similitud ${execution.cache_similarity.toFixed(3)}`}
        </dd>
        <dt>Guardarraíles</dt>
        <dd>
          entrada {execution.input_guardrail ?? '—'} · salida {execution.output_guardrail ?? '—'}
        </dd>
        <dt>Iteraciones del agente</dt>
        <dd>{execution.agent_iterations}</dd>
        <dt>Latencia</dt>
        <dd>{execution.latency_ms === null ? '—' : `${Math.round(execution.latency_ms)} ms`}</dd>
        <dt>Traza</dt>
        <dd className="mono">{report.trace_id ?? '—'}</dd>
        <dt>Análisis</dt>
        <dd className="mono">{report.analysis_id}</dd>
      </dl>
    </details>
  )
}

function ModelConfigurationPanel() {
  const api = useApi()
  const load = useCallback(() => api.configuration(), [api])
  const config = useAsync(load)
  return (
    <details className="card model-configuration">
      <summary>Configuración de modelos</summary>
      {config.error !== null && <ErrorNotice error={config.error} onRetry={config.reload} />}
      {config.data && (
        <dl className="definition-grid small">
          {Object.entries(config.data.text_models).map(([alias, model]) => (
            <Fragment key={alias}>
              <dt>Alias {alias}</dt>
              <dd className="mono">{model}</dd>
            </Fragment>
          ))}
          <dt>Embeddings</dt>
          <dd className="mono">{config.data.embedding_model}</dd>
          <dt>Políticas</dt>
          <dd>
            {config.data.breed_match_policy} · {config.data.router_policy} ·{' '}
            {config.data.guardrail_policy}
          </dd>
          <dt>Cobertura mínima</dt>
          <dd>{percent(config.data.breed_match_minimum_coverage)}</dd>
          <dt>Umbral de caché semántica</dt>
          <dd>{config.data.semantic_cache_threshold}</dd>
          <dt>Iteraciones máximas del agente</dt>
          <dd>{config.data.agent_max_iterations}</dd>
        </dl>
      )}
    </details>
  )
}
