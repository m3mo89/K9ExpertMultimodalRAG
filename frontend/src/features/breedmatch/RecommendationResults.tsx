import { useEffect, useState } from 'react'
import { useApi } from '../../api/hooks'
import type { HunterRecommendation, StructuredBreedProfile } from '../../api/types'
import { dimensionLabels, recommendationLimitation, recommendationPenalty } from '../../labels'

const bandLabel = { high: 'Alta', moderate: 'Moderada', low: 'Baja' }

// These limitations have their own notice instead of a line in the generic list.
const NOTICED_LIMITATIONS = new Set([
  'automatic_extraction_unreviewed', 'fewer_supported_candidates', 'no_candidate_reached_coverage',
])

function dimensionState(documented: boolean, conflicting: boolean, compatibility: number | null) {
  if (!documented) return 'No documentado'
  if (conflicting) return 'Evidencia contradictoria'
  return compatibility === 1 ? 'Coincide' : compatibility === 0 ? 'No coincide' : 'Parcial'
}

export function RecommendationResults({ result }: { result: HunterRecommendation }) {
  const api = useApi()
  const [profiles, setProfiles] = useState<Record<string, StructuredBreedProfile>>({})
  const [selected, setSelected] = useState<string[]>([])

  useEffect(() => {
    let active = true
    if (!result.snapshot_id) return () => { active = false }
    Promise.all(result.candidates.map(async (candidate) => [
      candidate.breed,
      await api.structuredBreedProfile(candidate.breed, result.snapshot_id as string),
    ] as const)).then((items) => {
      if (active) setProfiles(Object.fromEntries(items))
    }).catch(() => {
      // The deterministic result remains useful when optional profile details cannot load.
    })
    return () => { active = false }
  }, [api, result])

  const toggle = (breed: string) => setSelected((items) =>
    items.includes(breed) ? items.filter((item) => item !== breed) : [...items, breed].slice(0, 3)
  )
  const compared = result.candidates.filter((item) => selected.includes(item.breed))
  const dimensions = [...new Set(compared.flatMap((item) => item.dimensions.map((value) => value.key)))]
  const listedLimitations = result.limitations.filter((item) => !NOTICED_LIMITATIONS.has(item))

  return (
    <section className="card recommendation-results" aria-label="Recomendaciones">
      <h2>Recomendaciones documentadas</h2>
      <p className="small muted">
        La <strong>compatibilidad</strong> resume cuánto coincide la raza con su perfil en los aspectos
        que las fuentes documentan. La <strong>cobertura de evidencia</strong> indica qué parte de la presa,
        el trabajo y el terreno que eligió está documentada: un aspecto sin evidencia baja la cobertura, pero
        no cuenta a favor ni en contra.
      </p>
      {result.limitations.includes('automatic_extraction_unreviewed') && (
        <p className="notice notice-warn">
          Esta información se extrajo automáticamente de los documentos y ninguna persona la revisó.
          Compruébela en las páginas citadas antes de decidir.
        </p>
      )}
      {result.candidates.length === 0 && (
        <p className="notice notice-warn">
          Las fuentes no documentan lo suficiente sobre las respuestas elegidas para recomendar una raza.
          Pruebe a seleccionar más opciones o a añadir documentos a la biblioteca.
        </p>
      )}
      <div className="recommendation-grid">
        {result.candidates.map((candidate) => {
          const profile = profiles[candidate.breed]
          return (
            <article key={candidate.breed} className="recommendation-card">
              <h3>{candidate.breed}</h3>
              <p>
                Compatibilidad documentada:{' '}
                <strong>{candidate.band ? bandLabel[candidate.band] : 'Sin nivel'}</strong>
              </p>
              <p className="small">Cobertura de evidencia: {Math.round(candidate.coverage * 100)} %</p>
              <ul className="finding-list">
                {candidate.dimensions.map((dimension) => {
                  const attribute = profile?.attributes.find((item) => item.key === dimension.key)
                  const evidence = attribute?.assertions.flatMap((item) => item.evidence)
                    .filter((item, index, all) => dimension.evidence_ids.includes(item.fragment_id)
                      && all.findIndex((other) => other.fragment_id === item.fragment_id) === index)
                  return (
                    <li key={dimension.key}>
                      <strong>{dimensionLabels[dimension.key] ?? dimension.key}</strong>: {dimensionState(
                        dimension.documented, dimension.conflicting, dimension.compatibility,
                      )}
                      {evidence?.map((item) => (
                        <span className="citation-ref small" key={item.fragment_id}>
                          {' '}— <cite>{item.title}</cite>, pág. {item.physical_page}
                        </span>
                      ))}
                    </li>
                  )
                })}
              </ul>
              {candidate.penalties.length > 0 && (
                <p className="notice notice-warn small">{candidate.penalties.map(recommendationPenalty).join(' ')}</p>
              )}
              <label>
                <input
                  type="checkbox" checked={selected.includes(candidate.breed)}
                  disabled={!selected.includes(candidate.breed) && selected.length >= 3}
                  onChange={() => toggle(candidate.breed)}
                />{' '}Comparar {candidate.breed}
              </label>
            </article>
          )
        })}
      </div>
      {result.candidates.length > 0 && result.candidates.length < 3 && (
        <p className="small muted">Se muestran menos de tres razas porque las demás no alcanzan la cobertura mínima.</p>
      )}
      {compared.length >= 2 && (
        <div className="table-scroll" role="region" aria-label="Comparador de recomendaciones" tabIndex={0}>
          <table className="comparison-table">
            <caption>Comparación de {compared.length} razas</caption>
            <thead><tr><th scope="col">Dimensión</th>{compared.map((item) => <th scope="col" key={item.breed}>{item.breed}</th>)}</tr></thead>
            <tbody>
              {dimensions.map((key) => (
                <tr key={key}><th scope="row">{dimensionLabels[key] ?? key}</th>{compared.map((candidate) => {
                  const value = candidate.dimensions.find((item) => item.key === key)
                  return <td key={candidate.breed}>{value ? dimensionState(value.documented, value.conflicting, value.compatibility) : 'No documentado'}</td>
                })}</tr>
              ))}
              <tr><th scope="row">Cobertura</th>{compared.map((item) => <td key={item.breed}>{Math.round(item.coverage * 100)} %</td>)}</tr>
            </tbody>
          </table>
        </div>
      )}
      {listedLimitations.length > 0 && (
        <section aria-label="Limitaciones"><h3>Limitaciones</h3><ul>{listedLimitations.map((item) => <li key={item}>{recommendationLimitation(item)}</li>)}</ul></section>
      )}
    </section>
  )
}
