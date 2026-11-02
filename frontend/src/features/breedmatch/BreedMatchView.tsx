import { Fragment, useCallback, useId, useState, type FormEvent } from 'react'
import { useApi } from '../../api/hooks'
import type {
  BreedAnalysisResponse,
  BreedCandidate,
  BreedCriterion,
  CriterionKey,
  FindingOutcome,
} from '../../api/types'
import { BreedSuggestions } from '../../components/BreedSuggestions'
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
import { BreedProfileDialog } from './BreedProfileDialog'

export const MAX_CRITERIA = 12

/** Closed set of hunting functions; breeds and groups are discovered from the library. */
export const HUNTING_FUNCTIONS = ['rastro', 'muestra', 'cobro', 'busca', 'terrier', 'agua']

/**
 * Guided choices instead of free text: each option is a term the reference book uses, so it
 * can be found in the evidence. Vague words ("buena", "grande") would match almost anything.
 */
const GROUPS: { key: CriterionKey; question: string; options: string[] }[] = [
  { key: 'hunting_function', question: '¿Para qué caza lo quiere?', options: HUNTING_FUNCTIONS },
  {
    key: 'coat',
    question: '¿Qué manto prefiere?',
    options: ['pelo duro', 'pelo corto', 'pelo largo', 'sedoso', 'impermeable'],
  },
  {
    key: 'work_aptitude',
    question: '¿Qué trabajo debe hacer?',
    options: ['cubil', 'liebre', 'agua', 'olfato', 'obediencia'],
  },
]

/** An essential choice counts double in the score; the explanation shows the weights. */
const ESSENTIAL_WEIGHT = 2

const choiceId = (key: CriterionKey, value: string) => `${key}:${value}`

const outcomeTone: Record<FindingOutcome, 'ok' | 'error' | 'neutral'> = {
  match: 'ok',
  mismatch: 'error',
  not_documented: 'neutral',
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
  const breedListId = useId()
  // Selected choices in click order; the value is the criterion sent to the API.
  const [selected, setSelected] = useState<BreedCriterion[]>([
    { key: 'hunting_function', value: 'rastro', weight: 1 },
  ])
  const [breeds, setBreeds] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [report, setReport] = useState<BreedAnalysisResponse | null>(null)

  const find = (key: CriterionKey, value: string) =>
    selected.find((item) => choiceId(item.key, item.value) === choiceId(key, value))

  const toggle = (key: CriterionKey, value: string) =>
    setSelected((items) =>
      find(key, value)
        ? items.filter((item) => choiceId(item.key, item.value) !== choiceId(key, value))
        : [...items, { key, value, weight: 1 }],
    )

  const toggleEssential = (key: CriterionKey, value: string) =>
    setSelected((items) =>
      items.map((item) =>
        choiceId(item.key, item.value) === choiceId(key, value)
          ? { ...item, weight: item.weight > 1 ? 1 : ESSENTIAL_WEIGHT }
          : item,
      ),
    )

  const usable = selected

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (pending || usable.length === 0) return
    setPending(true)
    setError(null)
    try {
      const response = await api.submitBreedAnalysis({
        criteria: usable,
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
          Elija lo que necesita de su perro de caza. K9 BreedMatch busca en la biblioteca las
          razas que lo documentan y explica cada coincidencia con su página.
        </p>
      </header>
      <form className="card criteria-form" onSubmit={submit} aria-label="Criterios de análisis">
        {GROUPS.map((group) => (
          <fieldset key={group.key} className="choice-group">
            <legend className="section-label">{group.question}</legend>
            <div className="chip-row">
              {group.options.map((value) => {
                const choice = find(group.key, value)
                const essential = (choice?.weight ?? 0) > 1
                return (
                  <span key={value} className="chip-pair">
                    <button
                      type="button"
                      className="chip"
                      aria-pressed={Boolean(choice)}
                      disabled={!choice && selected.length >= MAX_CRITERIA}
                      onClick={() => toggle(group.key, value)}
                    >
                      {value}
                    </button>
                    {choice && (
                      <button
                        type="button"
                        className="chip-star"
                        aria-pressed={essential}
                        aria-label={`Imprescindible: ${value}`}
                        title="Imprescindible (cuenta doble)"
                        onClick={() => toggleEssential(group.key, value)}
                      >
                        {essential ? '★' : '☆'}
                      </button>
                    )}
                  </span>
                )
              })}
            </div>
          </fieldset>
        ))}
        <p className="small muted" aria-live="polite">
          {selected.length === 0
            ? 'Elija al menos una opción.'
            : `Ha elegido: ${selected
                .map((item) => `${item.value}${item.weight > 1 ? ' ★' : ''}`)
                .join(', ')}. Marque ★ lo imprescindible: cuenta doble.`}
        </p>
        <details className="breed-scope">
          <summary>Comparar sólo razas concretas (opcional)</summary>
          <label htmlFor={breedsId} className="small">
            Razas a comparar, separadas por comas. Si lo deja vacío, K9 busca las razas con
            más evidencia para lo que ha elegido.
          </label>
          <input
            id={breedsId}
            type="text"
            list={breedListId}
            value={breeds}
            placeholder="p. ej. Pointer, Setter inglés"
            onChange={(event) => setBreeds(event.target.value)}
          />
          <BreedSuggestions id={breedListId} />
        </details>
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
  const [profileBreed, setProfileBreed] = useState<string | null>(null)
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
          <ComparisonTable report={report} onOpen={setProfileBreed} />
          <ScoreExplanation report={report} />
          <h3 className="section-label">Evidencia por raza</h3>
          {report.candidates.map((candidate) => (
            <CandidateEvidence
              key={candidate.breed}
              candidate={candidate}
              onOpen={setProfileBreed}
            />
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
      {profileBreed && (
        <BreedProfileDialog breed={profileBreed} onClose={() => setProfileBreed(null)} />
      )}
    </section>
  )
}

function ComparisonTable({
  report,
  onOpen,
}: {
  report: BreedAnalysisResponse
  onOpen: (breed: string) => void
}) {
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
              <th scope="row">
                <button
                  type="button"
                  className="button-link breed-link"
                  aria-label={`Ver ficha de ${candidate.breed}`}
                  onClick={() => onOpen(candidate.breed)}
                >
                  {candidate.breed}
                </button>
              </th>
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

function CandidateEvidence({
  candidate,
  onOpen,
}: {
  candidate: BreedCandidate
  onOpen: (breed: string) => void
}) {
  return (
    <details className="candidate-evidence">
      <summary>{candidate.breed}</summary>
      <button type="button" className="button-secondary" onClick={() => onOpen(candidate.breed)}>
        Ver ficha de {candidate.breed}
      </button>
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
