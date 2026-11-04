import { describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, API_BASE } from './client'

describe('ApiClient', () => {
  it('only targets the same-origin application API', async () => {
    const fetchImpl = vi.fn(async () => new Response('[]', { status: 200 }))
    await new ApiClient(fetchImpl as typeof fetch).listDocuments()
    expect(API_BASE).toBe('/api/v1')
    expect(fetchImpl).toHaveBeenCalledWith('/api/v1/documents', expect.objectContaining({ method: 'GET' }))
  })

  it('maps the common error envelope to a typed error', async () => {
    const envelope = { code: 'feedback_comment_too_long', message: 'x', details: null, trace_id: 'abc', retryable: false }
    const client = new ApiClient((async () => new Response(JSON.stringify(envelope), { status: 422 })) as typeof fetch)
    const error = await client.submitFeedback('a', true, 'x').catch((reason: unknown) => reason)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, code: 'feedback_comment_too_long', traceId: 'abc', retryable: false })
  })

  it('treats network failures and non-envelope 5xx responses as retryable', async () => {
    const offline = new ApiClient((async () => {
      throw new TypeError('Failed to fetch')
    }) as typeof fetch)
    await expect(offline.health()).rejects.toMatchObject({ code: 'network_unavailable', retryable: true })
    const broken = new ApiClient((async () => new Response('<html>', { status: 502 })) as typeof fetch)
    await expect(broken.health()).rejects.toMatchObject({ code: 'unexpected_response', retryable: true })
  })

  it('sends administrative credentials only on administrative calls', async () => {
    const fetchImpl = vi.fn(async () => new Response('{}', { status: 200 }))
    const client = new ApiClient(fetchImpl as typeof fetch)
    await client.deactivate({ secret: 's3cret', actor: 'ana' }, 'doc-1')
    await client.listDocuments()
    const [[, adminInit], [, publicInit]] = fetchImpl.mock.calls as unknown as [string, RequestInit][]
    expect(adminInit.headers).toMatchObject({ 'X-K9-Admin-Secret': 's3cret', 'X-K9-Actor': 'ana' })
    expect(publicInit.headers).not.toHaveProperty('X-K9-Admin-Secret')
  })

  it('uses versioned immutable recommendation-context routes', async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({
      id: 'ctx', recommendation_id: 'rec', selected_breeds: ['Raza'], allowed_evidence: ['f1'], created_at: 't',
    }), { status: 201 }))
    const client = new ApiClient(fetchImpl as typeof fetch)
    await client.createRecommendationContext('rec', ['Raza'])
    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/v2/recommendations/rec/chat-context',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ selected_breeds: ['Raza'] }) }),
    )
  })
})
