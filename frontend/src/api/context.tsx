import { useMemo, useState, type ReactNode } from 'react'
import { ApiClient } from './client'
import { AdminContext, ApiContext } from './hooks'
import type { AdminCredentials } from './types'

/**
 * Administrative credentials live only in memory for the tab's lifetime; they are never
 * written to storage, so closing or reloading the page signs the administrator out.
 */
export function ApiProvider({ client, children }: { client?: ApiClient; children: ReactNode }) {
  const api = useMemo(() => client ?? new ApiClient(), [client])
  const [credentials, setCredentials] = useState<AdminCredentials | null>(null)
  const admin = useMemo(() => ({ credentials, setCredentials }), [credentials])
  return (
    <ApiContext.Provider value={api}>
      <AdminContext.Provider value={admin}>{children}</AdminContext.Provider>
    </ApiContext.Provider>
  )
}
