import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useApi } from '../../api/hooks'
import type {
  HunterProfileAnswer,
  HunterRecommendation,
  ProfileDimension,
} from '../../api/types'
import { ErrorNotice } from '../../components/ErrorNotice'
import { RecommendationResults } from './RecommendationResults'

interface Step {
  key: string
  question: string
  multiple: boolean
  options: Array<{ value: string; label: string; help?: string }>
}

const STEPS: Step[] = [
  {
    key: 'prey', question: '¿Qué desea cazar?', multiple: true,
    options: [
      ['venado', 'Venado'], ['jabalí', 'Jabalí'], ['conejo', 'Conejo'],
      ['liebre', 'Liebre'], ['aves', 'Aves'], ['varias_especies', 'Diferentes especies'],
    ].map(([value, label]) => ({ value, label })),
  },
  {
    key: 'modality', question: '¿Qué espera que haga el perro?', multiple: true,
    options: [
      { value: 'rastreo', label: 'Seguir un rastro', help: 'Seguir el olor dejado por una pieza.' },
      { value: 'rastro_herido', label: 'Localizar una pieza herida', help: 'Seguir su rastro después del disparo.' },
      { value: 'muestra', label: 'Señalar la pieza', help: 'Localizarla y señalarla sin levantarla.' },
      { value: 'cobro', label: 'Cobrar', help: 'Recuperar y entregar la pieza abatida.' },
      { value: 'levantamiento', label: 'Levantar piezas', help: 'Buscar y hacer salir la pieza.' },
      { value: 'agua', label: 'Trabajar en agua', help: 'Buscar o cobrar en humedales y agua.' },
    ],
  },
  {
    key: 'terrain', question: '¿Dónde caza principalmente?', multiple: true,
    options: [
      ['monte_denso', 'Monte denso'], ['bosque', 'Bosque'], ['campo_abierto', 'Campo abierto'],
      ['montana', 'Montaña'], ['accidentado', 'Terreno accidentado'], ['humedal', 'Humedales'],
    ].map(([value, label]) => ({ value, label })),
  },
  {
    key: 'experience', question: '¿Qué experiencia tiene con perros de trabajo?', multiple: false,
    options: [
      ['principiante', 'Principiante'], ['intermedia', 'Intermedia'], ['avanzada', 'Avanzada'],
    ].map(([value, label]) => ({ value, label })),
  },
  {
    key: 'daily_availability',
    question: '¿Cuánto tiempo diario puede dedicar a ejercicio y entrenamiento?', multiple: false,
    options: [
      ['menos_1h', 'Menos de una hora'], ['1_2h', 'Entre una y dos horas'],
      ['mas_2h', 'Más de dos horas'],
    ].map(([value, label]) => ({ value, label })),
  },
]

function labelFor(key: string, value: string): string {
  return STEPS.find((step) => step.key === key)?.options.find((item) => item.value === value)?.label ?? value
}

export function GuidedBreedMatch() {
  const api = useApi()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string[]>>({})
  const [dimensions, setDimensions] = useState<ProfileDimension[]>([])
  const [result, setResult] = useState<HunterRecommendation | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [pending, setPending] = useState(false)
  const current = STEPS[step]
  const summary = step === STEPS.length
  const request = useMemo(() => ({
    schema_version: '2.0' as const,
    answers: Object.entries(answers).map(([key, values]): HunterProfileAnswer => ({ key, values })),
  }), [answers])

  const toggle = (value: string) => {
    if (!current) return
    setAnswers((stored) => {
      const selected = stored[current.key] ?? []
      return {
        ...stored,
        [current.key]: current.multiple
          ? selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]
          : [value],
      }
    })
  }

  const next = async () => {
    if (!current || !(answers[current.key]?.length)) return
    if (step < STEPS.length - 1) {
      setStep(step + 1)
      return
    }
    setPending(true)
    setError(null)
    try {
      const validation = await api.validateHunterProfile(request)
      setDimensions(validation.dimensions)
      setStep(STEPS.length)
    } catch (reason) {
      setError(reason)
    } finally {
      setPending(false)
    }
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      setResult(await api.submitRecommendation(request))
    } catch (reason) {
      setError(reason)
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="guided-match" aria-labelledby="guided-heading">
      <header className="page-header">
        <h1 id="guided-heading">Encuentra tu perro de caza ideal</h1>
        <p className="muted">Responde cinco preguntas. Separaremos compatibilidad y evidencia disponible.</p>
      </header>
      <div className="card guided-card">
        <p className="small" aria-live="polite">Paso {Math.min(step + 1, 5)} de 5</p>
        <progress value={Math.min(step + 1, 5)} max={5} aria-label="Progreso del perfil" />
        {!summary && current && (
          <fieldset className="choice-group">
            <legend className="section-label">{current.question}</legend>
            <div className="guided-options">
              {current.options.map((option) => (
                <div key={option.value} className="guided-option">
                  <button
                    type="button" className="chip"
                    aria-pressed={(answers[current.key] ?? []).includes(option.value)}
                    onClick={() => toggle(option.value)}
                  >{option.label}</button>
                  {option.help && <details><summary>¿Qué significa?</summary><p className="small">{option.help}</p></details>}
                </div>
              ))}
            </div>
            <div className="button-row">
              {step > 0 && <button type="button" className="button-secondary" onClick={() => setStep(step - 1)}>Atrás</button>}
              <button
                type="button" className="button-primary"
                disabled={pending || !(answers[current.key]?.length)} onClick={next}
              >{step === 4 ? 'Revisar perfil' : 'Continuar'}</button>
            </div>
          </fieldset>
        )}
        {summary && (
          <form onSubmit={submit} aria-label="Resumen del perfil">
            <h2>Revisa tu perfil</h2>
            <dl className="definition-grid">
              {STEPS.map((item, index) => (
                <div key={item.key}>
                  <dt>{item.question}</dt>
                  <dd>
                    {(answers[item.key] ?? []).map((value) => labelFor(item.key, value)).join(', ')}{' '}
                    <button type="button" className="button-link" onClick={() => setStep(index)}>Editar</button>
                  </dd>
                </div>
              ))}
            </dl>
            <details><summary>Interpretación normalizada</summary><ul>{dimensions.map((item) => <li key={item.key}>{item.key}: {item.values.join(', ')}</li>)}</ul></details>
            <div className="button-row">
              <button type="button" className="button-secondary" onClick={() => setStep(4)}>Atrás</button>
              <button type="submit" className="button-primary" disabled={pending}>{pending ? 'Buscando…' : 'Ver recomendaciones'}</button>
            </div>
          </form>
        )}
        {error !== null && <ErrorNotice error={error} />}
      </div>
      {result && <RecommendationResults result={result} />}
    </section>
  )
}
