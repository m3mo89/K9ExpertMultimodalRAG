import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { fakeApi, renderWithApi } from '../../test/fakeApi'
import { GuidedBreedMatch } from './GuidedBreedMatch'

const validation = {
  schema_version: '2.0', translator_version: 'hunter-profile-v1', completeness: 'complete',
  missing_fields: [], constraints: [],
  dimensions: [
    { key: 'prey', values: ['venado'], weight: 0.3, required: true },
    { key: 'modality', values: ['rastreo'], weight: 0.3, required: true },
    { key: 'terrain', values: ['monte_denso'], weight: 0.25, required: true },
    { key: 'experience', values: ['principiante'], weight: 0.2, required: true },
    { key: 'daily_availability', values: ['1_2h'], weight: 0.15, required: true },
  ],
}

function setup() {
  return fakeApi({
    'POST /api/v2/hunter-profiles/validate': validation,
    'POST /api/v2/recommendations': {
      schema_version: '2.0', recommendation_id: 'r1', status: 'completed',
      policy_version: 'recommendation-v2-draft', snapshot_id: 's1', trace_id: 't1', summary: null,
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
  for (const label of ['Venado', 'Seguir un rastro', 'Monte denso', 'Principiante', 'Entre una y dos horas']) {
    await user.click(screen.getByRole('button', { name: label }))
    await user.click(screen.getByRole('button', { name: /Continuar|Revisar perfil/ }))
  }
  return user
}

describe('GuidedBreedMatch', () => {
  it('navigates five steps, explains terminology and preserves answers', async () => {
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
    expect(screen.getByText('prey: venado')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Editar' })).toHaveLength(5)
    await user.click(screen.getByRole('button', { name: 'Ver recomendaciones' }))
    expect(await screen.findByRole('region', { name: 'Recomendaciones' })).toHaveTextContent('Raza')
    expect(api.requests.some((item) => item.url === '/api/v2/recommendations')).toBe(true)
  })
})
