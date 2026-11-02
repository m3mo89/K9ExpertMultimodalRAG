import { useCallback } from 'react'
import { useApi } from '../api/hooks'
import { useAsync } from '../hooks'

/**
 * Suggestions for breed inputs, taken from the breeds the active library documents. Free text
 * stays accepted; the backend resolves names and reports unknown ones.
 */
export function BreedSuggestions({ id }: { id: string }) {
  const api = useApi()
  const { data } = useAsync(useCallback(() => api.listBreeds(), [api]))
  return (
    <datalist id={id}>
      {(data ?? []).map((breed) => (
        <option key={breed.name} value={breed.name} />
      ))}
    </datalist>
  )
}
