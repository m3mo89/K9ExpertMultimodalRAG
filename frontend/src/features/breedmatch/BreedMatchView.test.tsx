import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { analysisFixture, configurationFixture } from '../../test/breedMatchFixture'
import { errorBody, fakeApi, renderWithApi } from '../../test/fakeApi'
import { BreedMatchView } from './BreedMatchView'

function setup(analysis: unknown = { status: 201, body: analysisFixture }, extra: Record<string, unknown> = {}) {
  return fakeApi({
    'POST /breed-analyses': analysis,
    'GET /configuration': configurationFixture,
    ...extra,
  })
}

async function analyze() {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Añadir criterio' }))
  await user.type(screen.getByLabelText('Valor del criterio 2'), 'pelo duro')
  await user.type(screen.getByLabelText(/Razas a comparar/), 'Teckel alemán, Basset hound')
  await user.click(screen.getByRole('button', { name: 'Analizar razas' }))
  return user
}

describe('BreedMatchView', () => {
  it('submits structured criteria and renders the cited comparison report', async () => {
    const api = setup()
    renderWithApi(<BreedMatchView />, api.client)
    await analyze()

    const report = await screen.findByRole('region', { name: 'Informe de análisis' })
    expect(within(report).getByText('Análisis completo')).toBeInTheDocument()
    expect(within(report).getByText(analysisFixture.summary)).toBeInTheDocument()

    const table = within(report).getByRole('table', { name: 'Comparación por criterio' })
    const teckel = within(table).getByRole('row', { name: /Teckel alemán/ })
    expect(within(teckel).getByText('Coincide')).toBeInTheDocument()
    expect(within(teckel).getByText('No documentado')).toBeInTheDocument()
    expect(within(teckel).getByText('100 %')).toBeInTheDocument()
    const basset = within(table).getByRole('row', { name: /Basset hound/ })
    expect(within(basset).getByText('Sin puntuación')).toBeInTheDocument()

    const explanation = within(report).getByRole('region', { name: 'Explicación de la puntuación' })
    expect(within(explanation).getByText(/2 ÷ 2 = 100 %/)).toBeInTheDocument()
    expect(within(report).getByText(/pág\. 40 \(PDF 42\)/)).toBeInTheDocument()
    expect(within(report).getByText('No todos los criterios están documentados.')).toBeInTheDocument()
    expect(within(report).getByText('trace-9')).toBeInTheDocument()
    expect(within(report).getByText('entrada allow · salida allow')).toBeInTheDocument()

    const request = api.requests.find((item) => item.url === '/api/v1/breed-analyses')
    expect(request?.body).toEqual({
      criteria: [
        { key: 'hunting_function', value: 'rastro', weight: 1 },
        { key: 'coat', value: 'pelo duro', weight: 1 },
      ],
      candidate_breeds: ['Teckel alemán', 'Basset hound'],
      document_ids: [],
    })
    expect(api.requests.some((item) => /queries|conversations/.test(item.url))).toBe(false)
  })

  it('records useful feedback for the analysis', async () => {
    const api = setup(undefined, {
      'POST /breed-analyses/an-1/feedback': {
        status: 201,
        body: { id: 'f', analysis_id: 'an-1', trace_id: 'trace-9', useful: 1, comment: null, created_at: 't' },
      },
    })
    renderWithApi(<BreedMatchView />, api.client)
    const user = await analyze()
    const feedback = await screen.findByRole('form', { name: 'Valorar análisis' })
    await user.click(within(feedback).getByRole('button', { name: 'Útil' }))
    await user.click(within(feedback).getByRole('button', { name: 'Enviar valoración' }))
    expect(await screen.findByText(/su valoración quedó registrada/)).toBeInTheDocument()
    const sent = api.requests.find((item) => item.url === '/api/v1/breed-analyses/an-1/feedback')
    expect(sent?.body).toEqual({ useful: true, comment: null })
  })

  it('explains a rejected analysis with its guardrail reason', async () => {
    const api = setup({
      status: 201,
      body: { ...analysisFixture, status: 'rejected', reason: 'prompt_injection_detected', candidates: [], summary: null, limitations: [] },
    })
    renderWithApi(<BreedMatchView />, api.client)
    await analyze()
    const report = await screen.findByRole('region', { name: 'Informe de análisis' })
    expect(within(report).getByText('Criterios rechazados')).toBeInTheDocument()
    expect(within(report).getByText('Los criterios contienen instrucciones no permitidas.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows API errors and shows safe model configuration', async () => {
    const api = setup({ status: 503, body: errorBody('internal_error', true) })
    renderWithApi(<BreedMatchView />, api.client)
    await analyze()
    expect(await screen.findByRole('alert')).toHaveTextContent('El servidor no pudo completar')
    expect(await screen.findByText('qwen3.5:2b')).toBeInTheDocument()
    expect(screen.getByText('Alias complex')).toBeInTheDocument()
  })
})
