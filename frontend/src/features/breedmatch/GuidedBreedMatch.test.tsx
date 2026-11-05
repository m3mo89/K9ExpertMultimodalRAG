import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { fakeApi, renderWithApi } from '../../test/fakeApi'
import { GuidedBreedMatch } from './GuidedBreedMatch'

const validation = {
  schema_version: '2.0', translator_version: 'hunter-profile-v2', completeness: 'complete',
  missing_fields: [], constraints: [],
  dimensions: [
    { key: 'prey', values: ['venado'], weight: 0.3, required: true },
    { key: 'modality', values: ['rastreo'], weight: 0.3, required: true },
    { key: 'terrain', values: ['monte_denso'], weight: 0.25, required: true },
  ],
}

function setup() {
  return fakeApi({
    'POST /api/v2/hunter-profiles/validate': validation,
    'POST /api/v2/recommendations': {
      schema_version: '2.0', recommendation_id: 'r1', status: 'completed',
      policy_version: 'recommendation-v3', snapshot_id: 's1', trace_id: 't1', summary: null,
      limitations: ['narrative_unavailable'],
      candidates: [{
        breed: 'Raza', band: 'high', compatibility: 1, coverage: 0.7,
        penalties: [], excluded: false, dimensions: [],
      }],
    },
  })
}

async function complete(api: ReturnType<typeof setup>) {
  const user = userEvent.setup()
  renderWithApi(<GuidedBreedMatch />, api.client)
  for (const label of ['Venado', 'Seguir un rastro', 'Monte denso']) {
    await user.click(screen.getByRole('button', { name: label }))
    await user.click(screen.getByRole('button', { name: /Continuar|Revisar perfil/ }))
  }
  return user
}

describe('GuidedBreedMatch', () => {
  it('navigates three steps, explains terminology and preserves answers', async () => {
    const api = setup()
    const user = userEvent.setup()
    renderWithApi(<GuidedBreedMatch />, api.client)
    await user.click(screen.getByRole('button', { name: 'Venado' }))
    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    await user.click(screen.getAllByText('¿Qué significa?')[0])
    expect(screen.getByText(/Seguir el olor/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Atrás' }))
    expect(screen.getByRole('button', { name: 'Venado' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('blocks continuation when a decision-critical answer is missing', () => {
    renderWithApi(<GuidedBreedMatch />, setup().client)
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeDisabled()
  })

  it('shows editable original and normalized summaries then recommendations', async () => {
    const api = setup()
    const user = await complete(api)
    expect(await screen.findByRole('form', { name: 'Resumen del perfil' })).toBeInTheDocument()
    expect(screen.getByText('Presa: Venado')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Editar' })).toHaveLength(3)
    await user.click(screen.getByRole('button', { name: 'Ver recomendaciones' }))
    expect(await screen.findByRole('region', { name: 'Recomendaciones' })).toHaveTextContent('Raza')
    expect(api.requests.some((item) => item.url === '/api/v2/recommendations')).toBe(true)
  })

  it('only asks what the policy can evaluate', async () => {
    const api = setup()
    await complete(api)
    await screen.findByRole('form', { name: 'Resumen del perfil' })
    expect(screen.queryByText(/experiencia/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/tiempo diario/i)).not.toBeInTheDocument()
    expect(screen.getByText('Paso 3 de 3')).toBeInTheDocument()
  })
})
