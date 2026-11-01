import { createContext, useContext } from 'react'
import type { ApiClient } from './client'
import type { AdminCredentials } from './types'

export interface AdminState {
  credentials: AdminCredentials | null
  setCredentials: (credentials: AdminCredentials | null) => void
}

export const ApiContext = createContext<ApiClient | null>(null)
export const AdminContext = createContext<AdminState | null>(null)

export function useApi(): ApiClient {
  const api = useContext(ApiContext)
  if (!api) throw new Error('useApi must be used inside ApiProvider')
  return api
}

export function useAdmin(): AdminState {
  const admin = useContext(AdminContext)
  if (!admin) throw new Error('useAdmin must be used inside ApiProvider')
  return admin
}
