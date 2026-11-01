import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { vi } from 'vitest'
import { ApiClient } from '../api/client'
import { ApiProvider } from '../api/context'

export interface RecordedRequest {
  method: string
  url: string
  headers: Record<string, string>
  body: unknown
}

type Handler = (request: RecordedRequest) => { status?: number; body: unknown }

function isResponseSpec(value: unknown): value is { status: number; body: unknown } {
  if (typeof value !== 'object' || value === null) return false
  const keys = Object.keys(value).sort()
  return keys.length === 2 && keys[0] === 'body' && keys[1] === 'status'
}

/** Routes "METHOD /path" (path relative to /api/v1, query string ignored) to canned responses. */
export function fakeApi(routes: Record<string, Handler | unknown>) {
  const requests: RecordedRequest[] = []
  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method ?? 'GET'
    const raw = init?.body
    const request: RecordedRequest = {
      method,
      url,
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: typeof raw === 'string' ? JSON.parse(raw) : raw,
    }
    requests.push(request)
    const path = url.replace(/^\/api\/v1/, '').split('?')[0]
    const route = routes[`${method} ${path}`]
    if (route === undefined) {
      return new Response(JSON.stringify({ code: 'not_mocked', message: url, trace_id: 't', retryable: false, details: null }), {
        status: 404,
      })
    }
    const result =
      typeof route === 'function'
        ? (route as Handler)(request)
        : isResponseSpec(route)
          ? route
          : { body: route }
    return new Response(JSON.stringify(result.body), { status: result.status ?? 200 })
  })
  return { client: new ApiClient(fetchImpl as typeof fetch), requests, fetchImpl }
}

export function renderWithApi(ui: ReactElement, client: ApiClient) {
  return render(<ApiProvider client={client}>{ui}</ApiProvider>)
}

export function errorBody(code: string, retryable = false) {
  return { code, message: code, details: null, trace_id: 'trace-1', retryable }
}

export const documentFixture = {
  id: 'doc-1',
  title: 'Enciclopedia de perros de caza',
  author: 'Autor',
  category: 'caza',
  status: 'active',
  active_version_id: 'ver-1',
  edition: '2',
  updated_at: '2026-11-01T00:00:00+00:00',
}

export const citationFixture = {
  id: 'cit-1',
  fragment_id: 'frag-1',
  document_id: 'doc-1',
  version_id: 'ver-1',
  title: 'Enciclopedia de perros de caza',
  author: 'Autor',
  edition: '2',
  physical_page: 42,
  printed_page_label: '40',
  source_status: 'active',
}
