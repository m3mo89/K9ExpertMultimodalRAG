import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { fakeApi, renderWithApi } from '../../test/fakeApi'
import { SystemView } from './SystemView'

describe('SystemView', () => {
  it('highlights degraded components and basic metrics', async () => {
    const api = fakeApi({
      'GET /health': { status: 'ok', worker_concurrency: 1 },
      'GET /admin/health': {
        status: 'degraded',
        checked_at: '2026-11-01T00:00:00Z',
        components: {
          api: { status: 'ok', detail: 'serving' },
          inference: { status: 'degraded', detail: 'inference_unreachable' },
          worker: { status: 'degraded', detail: 'worker_heartbeat_stale' },
        },
      },
      'GET /admin/metrics': {
        generated_at: '2026-11-01T00:00:00Z',
        queries: { grounded: 3, abstained: 1 },
        documents: { active: 2 },
        jobs: { available: 2 },
        feedback: { useful: 2, not_useful: 1 },
        recent: {
          window_hours: 24,
          query_states: { grounded: 3, abstained: 1 },
          abstention_rate: 0.25,
          latency_ms: { count: 4, p50: 812.4, p95: 2400 },
          cache: { hits: 2, misses: 2 },
          generation_calls: 2,
          ingestion: { jobs_completed: 1, jobs_failed: 0, pages: 243, ocr_pages: 4, fragments: 900, pages_per_minute: 61.5 },
          errors: {},
          layers: {
            latency_ms: { retrieval: { count: 2, p50: 40, p95: 90 } },
            guardrails: { 'input_guardrail:block:prompt_injection_detected': 1 },
            cache: { query: { miss: 2 }, breed_analysis: { miss: 1, semantic: 1 } },
            routes: { simple: 1 },
            route_reasons: { bounded_request: 1 },
            resolved_models: { 'llama3.2:3b': 1 },
            fallback_used: 0,
            agent_iterations: { '1': 1 },
            breed_match_states: { completed: 2 },
            breed_match_feedback: [],
          },
        },
      },
    })
    renderWithApi(<SystemView />, api.client)
    expect(await screen.findByText(/concurrencia del trabajador: 1/)).toBeInTheDocument()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Secreto administrativo'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Estado general:', { exact: false })).toHaveTextContent('Degradado')
    expect(screen.getByText('El trabajador no envía señal de vida reciente.')).toBeInTheDocument()
    expect(screen.getByText('Modelos locales')).toBeInTheDocument()
    expect(await screen.findByText('25 %')).toBeInTheDocument()
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(screen.getByText('812 ms / 2400 ms')).toBeInTheDocument()
    expect(screen.getByText('50 %')).toBeInTheDocument()
    expect(screen.getByText('61.5')).toBeInTheDocument()
    expect(screen.getByText('Capas de ejecución de IA')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Caché de análisis' })).toHaveTextContent('Caché semántica')
    expect(screen.getByRole('table', { name: 'Análisis de razas por resultado' })).toHaveTextContent('Análisis completo')
  })
})
