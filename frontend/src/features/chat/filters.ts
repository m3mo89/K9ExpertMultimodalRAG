import type { QueryFilters } from '../../api/types'

export const emptyFilters: QueryFilters = { document_ids: [], categories: [], breeds: [], sections: [] }

export function filterCount(filters: QueryFilters): number {
  return (
    filters.document_ids.length +
    filters.categories.length +
    filters.breeds.length +
    filters.sections.length
  )
}
