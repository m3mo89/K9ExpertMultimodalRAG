import { useId } from 'react'
import type { DocumentSummary, QueryFilters } from '../../api/types'
import { BreedSuggestions } from '../../components/BreedSuggestions'
import { emptyFilters, filterCount } from './filters'

function splitTerms(value: string): string[] {
  return value
    .split(',')
    .map((term) => term.trim())
    .filter(Boolean)
}

interface Props {
  documents: DocumentSummary[]
  filters: QueryFilters
  onChange: (filters: QueryFilters) => void
}

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

/** Strict source scope: the backend never broadens a filtered search. */
export function FilterPanel({ documents, filters, onChange }: Props) {
  const breedsId = useId()
  const breedListId = useId()
  const sectionsId = useId()
  const active = documents.filter((document) => document.status === 'active')
  const categories = [...new Set(active.map((document) => document.category).filter(Boolean))] as string[]
  const count = filterCount(filters)

  return (
    <details className="filters">
      <summary>
        Filtrar fuentes{count > 0 ? ` (${count} activos)` : ' (todas las fuentes activas)'}
      </summary>
      <div className="filters-body">
        <fieldset>
          <legend>Documentos</legend>
          {active.length === 0 && <p className="muted small">No hay documentos activos.</p>}
          {active.map((document) => (
            <label key={document.id} className="check">
              <input
                type="checkbox"
                checked={filters.document_ids.includes(document.id)}
                onChange={() =>
                  onChange({ ...filters, document_ids: toggle(filters.document_ids, document.id) })
                }
              />
              {document.title}
            </label>
          ))}
        </fieldset>
        {categories.length > 0 && (
          <fieldset>
            <legend>Categorías</legend>
            {categories.map((category) => (
              <label key={category} className="check">
                <input
                  type="checkbox"
                  checked={filters.categories.includes(category)}
                  onChange={() =>
                    onChange({ ...filters, categories: toggle(filters.categories, category) })
                  }
                />
                {category}
              </label>
            ))}
          </fieldset>
        )}
        <label htmlFor={breedsId}>Razas (separadas por comas)</label>
        <input
          id={breedsId}
          key={`breeds-${filters.breeds.join(',')}`}
          type="text"
          list={breedListId}
          defaultValue={filters.breeds.join(', ')}
          onBlur={(event) => onChange({ ...filters, breeds: splitTerms(event.target.value) })}
        />
        <BreedSuggestions id={breedListId} />
        <label htmlFor={sectionsId}>Secciones (separadas por comas)</label>
        <input
          id={sectionsId}
          key={`sections-${filters.sections.join(',')}`}
          type="text"
          defaultValue={filters.sections.join(', ')}
          onBlur={(event) => onChange({ ...filters, sections: splitTerms(event.target.value) })}
        />
        {count > 0 && (
          <button type="button" className="button-ghost" onClick={() => onChange(emptyFilters)}>
            Quitar filtros
          </button>
        )}
      </div>
    </details>
  )
}
