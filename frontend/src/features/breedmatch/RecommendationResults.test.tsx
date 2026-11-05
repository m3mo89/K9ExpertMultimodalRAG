import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { HunterRecommendation } from '../../api/types'
import { fakeApi, renderWithApi } from '../../test/fakeApi'
import { RecommendationResults } from './RecommendationResults'

const result: HunterRecommendation = {
  schema_version: '2.0', recommendation_id: 'r1', status: 'completed',
  policy_version: 'v2', snapshot_id: '11111111-1111-1111-1111-111111111111',
  trace_id: 't1', summary: null, limitations: [],
  candidates: [
    {
      breed: 'Raza A', band: 'high', compatibility: 1, coverage: 0.8,
      penalties: [], excluded: false,
      dimensions: [
        { key: 'modality', compatibility: 1, documented: true, conflicting: false, evidence_ids: ['f1'] },
        { key: 'terrain', compatibility: null, documented: false, conflicting: false, evidence_ids: [] },
      ],
    },
    {
      breed: 'Raza B', band: 'moderate', compatibility: 0.6, coverage: 0.6,
      penalties: ['documented_incompatibility:terrain'], excluded: false,
      dimensions: [
        { key: 'modality', compatibility: null, documented: true, conflicting: true, evidence_ids: ['f2'] },
        { key: 'terrain', compatibility: 0, documented: true, conflicting: false, evidence_ids: ['f3'] },
      ],
    },
  ],
}

function setup() {
  const profile = (breed: string, fragment: string) => ({
    breed, snapshot_id: result.snapshot_id, policy_version: 'v1',
    attributes: [{
      key: 'modality', evidence_state: 'documented',
      assertions: [{ id: `a-${fragment}`, value: 'rastreo', polarity: 'supports', evidence: [{
        fragment_id: fragment, title: 'Enciclopedia', physical_page: breed === 'Raza A' ? 12 : 20,
      }] }],
    }],
  })
  return fakeApi({
    'GET /api/v2/breeds/Raza%20A/structured-profile': profile('Raza A', 'f1'),
    'GET /api/v2/breeds/Raza%20B/structured-profile': profile('Raza B', 'f2'),
  })
}

describe('RecommendationResults', () => {
  it('shows bands, unknowns, conflicts, penalties, sources and fewer-than-three reason', async () => {
    renderWithApi(<RecommendationResults result={result} />, setup().client)
    expect(screen.getByText('Alta')).toBeInTheDocument()
    expect(screen.getByText((_text, node) => node?.textContent === 'Trabajo del perro: Evidencia contradictoria')).toBeInTheDocument()
    expect(screen.getByText((_text, node) => node?.textContent === 'Terreno: No documentado')).toBeInTheDocument()
    expect(screen.getByText(/documenta una incompatibilidad en: Terreno/)).toBeInTheDocument()
    expect(await screen.findByText(/pág. 12/)).toBeInTheDocument()
    expect(screen.getByText(/menos de tres razas/)).toBeInTheDocument()
  })

  it('explains that unknown aspects lower coverage without counting for or against', () => {
    renderWithApi(<RecommendationResults result={result} />, setup().client)
    expect(screen.getByText(/no cuenta a favor ni en contra/)).toBeInTheDocument()
  })

  it('discloses automatic extraction and translates limitation codes', () => {
    renderWithApi(<RecommendationResults result={{
      ...result,
      limitations: ['automatic_extraction_unreviewed', 'dimension_not_evaluated:experience', 'narrative_unavailable', 'fewer_supported_candidates'],
    }} />, setup().client)
    expect(screen.getByText(/ninguna persona la revisó/)).toBeInTheDocument()
    expect(screen.getByText(/Experiencia del propietario: las fuentes no permiten evaluarlo/)).toBeInTheDocument()
    expect(screen.getByText(/No se generó la síntesis narrativa/)).toBeInTheDocument()
    const region = screen.getByRole('region', { name: 'Recomendaciones' })
    expect(region).not.toHaveTextContent(/automatic_extraction|dimension_not_evaluated|narrative_unavailable|fewer_supported/)
  })

  it('explains an abstention in plain language', () => {
    renderWithApi(<RecommendationResults result={{
      ...result, status: 'abstained', candidates: [], limitations: ['no_candidate_reached_coverage'],
    }} />, setup().client)
    expect(screen.getByText(/no documentan lo suficiente/)).toBeInTheDocument()
    expect(screen.queryByText(/menos de tres razas/)).not.toBeInTheDocument()
    expect(screen.queryByText(/no_candidate_reached_coverage/)).not.toBeInTheDocument()
  })

  it('cites only the evidence behind each dimension, once', async () => {
    const api = fakeApi({
      'GET /api/v2/breeds/Raza%20A/structured-profile': {
        breed: 'Raza A', snapshot_id: result.snapshot_id, policy_version: 'v1',
        attributes: [{
          key: 'modality', evidence_state: 'documented',
          assertions: ['rastreo', 'cobro'].map((value) => ({
            id: value, value, polarity: 'supports', evidence: [
              { fragment_id: 'f1', title: 'Enciclopedia', physical_page: 12 },
              { fragment_id: 'other', title: 'Enciclopedia', physical_page: 99 },
            ],
          })),
        }],
      },
      'GET /api/v2/breeds/Raza%20B/structured-profile': {
        breed: 'Raza B', snapshot_id: result.snapshot_id, policy_version: 'v1', attributes: [],
      },
    })
    renderWithApi(<RecommendationResults result={result} />, api.client)
    expect(await screen.findAllByText(/pág. 12/)).toHaveLength(1)
    expect(screen.queryByText(/pág. 99/)).not.toBeInTheDocument()
  })

  it('compares two breeds in an accessible table', async () => {
    renderWithApi(<RecommendationResults result={result} />, setup().client)
    const user = userEvent.setup()
    await user.click(screen.getByLabelText('Comparar Raza A'))
    await user.click(screen.getByLabelText('Comparar Raza B'))
    const region = screen.getByRole('region', { name: 'Comparador de recomendaciones' })
    const table = within(region).getByRole('table', { name: 'Comparación de 2 razas' })
    expect(within(table).getByRole('row', { name: /Trabajo del perro/ })).toHaveTextContent('Coincide')
    expect(within(table).getByRole('row', { name: /Cobertura/ })).toHaveTextContent('80 %')
  })
})
