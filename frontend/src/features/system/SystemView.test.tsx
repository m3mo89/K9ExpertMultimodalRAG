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
  })
})
