import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { citationFixture, documentFixture, errorBody, fakeApi, renderWithApi } from '../../test/fakeApi'
import { ChatView } from './ChatView'

const conversation = { id: 'conv-1', created_at: 't', updated_at: 't', messages: [] }

function grounded(overrides: Record<string, unknown> = {}) {
  return {
    query_id: 'q-1',
    answer_id: 'ans-1',
    status: 'grounded',
    answer: 'El teckel es un perro tenaz.',
    snapshot_id: 'snap-1',
    reason: null,
    citations: [citationFixture],
    conversation_id: 'conv-1',
    ...overrides,
  }
}

function setup(query: unknown, extra: Record<string, unknown> = {}) {
  return fakeApi({
    'GET /conversations': [],
    'GET /documents': [documentFixture],
    'POST /conversations': { status: 201, body: conversation },
    'POST /queries': query,
    ...extra,
  })
}

async function ask(text: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Pregunta'), text)
  await user.click(screen.getByRole('button', { name: 'Preguntar' }))
  return user
}

describe('ChatView', () => {
  it('shows a grounded answer with citations and records feedback', async () => {
    const api = setup(grounded(), {
      'POST /answers/ans-1/feedback': { status: 201, body: { id: 'f', answer_id: 'ans-1', useful: 1, comment: null, created_at: 't' } },
    })
    renderWithApi(<ChatView />, api.client)
    const user = await ask('¿Cómo es el teckel?')

    expect(await screen.findByText('El teckel es un perro tenaz.')).toBeInTheDocument()
    expect(screen.getByText('Síntesis documental')).toBeInTheDocument()
    const sources = screen.getByRole('region', { name: 'Fuentes citadas' })
    expect(within(sources).getByText('Enciclopedia de perros de caza')).toBeInTheDocument()
    expect(within(sources).getByText('pág. 40 (PDF 42)')).toBeInTheDocument()
    expect(within(sources).getByText(/Autor · 2\.ª ed\./)).toBeInTheDocument()

    const query = api.requests.find((request) => request.url === '/api/v1/queries')
    expect(query?.body).toMatchObject({ text: '¿Cómo es el teckel?', conversation_id: 'conv-1' })

    await user.click(screen.getByRole('button', { name: 'Útil' }))
    await user.type(screen.getByLabelText(/Comentario opcional/), 'Muy clara')
    await user.click(screen.getByRole('button', { name: 'Enviar valoración' }))
    expect(await screen.findByText(/valoración quedó registrada/)).toBeInTheDocument()
    const feedback = api.requests.find((request) => request.url.endsWith('/feedback'))
    expect(feedback?.body).toEqual({ useful: true, comment: 'Muy clara' })
  })

  it('shows an explicit abstention without inventing an answer', async () => {
    const api = setup(grounded({ status: 'abstained', answer: '', reason: 'no_evidence', citations: [] }))
    renderWithApi(<ChatView />, api.client)
    await ask('¿Qué dice del perro lobo?')
    expect(await screen.findByText(/Aviso del sistema · Sin respaldo suficiente/)).toBeInTheDocument()
    expect(screen.getByText(/No se encontró respaldo documental suficiente en las fuentes seleccionadas/)).toBeInTheDocument()
    expect(screen.queryByText('Síntesis documental')).not.toBeInTheDocument()
  })

  it('never displays an unverified draft', async () => {
    const api = setup(grounded({ status: 'unverified', answer: 'Borrador inventado', citations: [] }))
    renderWithApi(<ChatView />, api.client)
    await ask('¿Qué dice del perro?')
    expect(await screen.findByText(/no pudieron vincularse a la evidencia/)).toBeInTheDocument()
    expect(screen.queryByText('Borrador inventado')).not.toBeInTheDocument()
  })

  it('offers retry for retryable failures and recovers', async () => {
    let calls = 0
    const api = setup(() => {
      calls += 1
      return calls === 1 ? { status: 503, body: errorBody('model_unavailable', true) } : { body: grounded() }
    })
    renderWithApi(<ChatView />, api.client)
    const user = await ask('¿Cómo es el teckel?')
    expect(await screen.findByRole('alert')).toHaveTextContent('Error: model_unavailable')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('El teckel es un perro tenaz.')).toBeInTheDocument()
    expect(calls).toBe(2)
  })

  it('sends selected source filters with the query', async () => {
    const api = setup(grounded())
    renderWithApi(<ChatView />, api.client)
    const user = userEvent.setup()
    await user.click(screen.getByText(/Filtrar fuentes/))
    await user.click(await screen.findByRole('checkbox', { name: documentFixture.title }))
    await user.type(screen.getByLabelText('Razas (separadas por comas)'), 'teckel, beagle')
    await user.tab()
    await ask('¿Cómo es el teckel?')
    await screen.findByText('El teckel es un perro tenaz.')
    const query = api.requests.find((request) => request.url === '/api/v1/queries')
    expect(query?.body).toMatchObject({
      filters: { document_ids: ['doc-1'], categories: [], breeds: ['teckel', 'beagle'], sections: [] },
    })
    expect(screen.getByText('Ámbito filtrado (3)')).toBeInTheDocument()
  })

  it('reopens a historical conversation with current source availability', async () => {
    const api = setup(grounded(), {
      'GET /conversations': [{ id: 'conv-9', title: '¿Origen del beagle?', created_at: 't', updated_at: '2026-11-01T00:00:00Z' }],
      'GET /conversations/conv-9': {
        ...conversation,
        id: 'conv-9',
        messages: [
          {
            query_id: 'q-9',
            question: '¿Origen del beagle?',
            snapshot_id: 'snap-0',
            status: 'grounded',
            created_at: 't',
            answer_id: 'ans-9',
            answer: 'Procede de Inglaterra.',
            citations: [{ ...citationFixture, current_source_status: 'deleted' }],
          },
        ],
      },
    })
    renderWithApi(<ChatView />, api.client)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /¿Origen del beagle\?/ }))
    expect(await screen.findByText('Procede de Inglaterra.')).toBeInTheDocument()
    expect(screen.getByText('Eliminada')).toBeInTheDocument()
    expect(screen.getByText('Se conserva la cita tal como se produjo.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: /¿Origen del beagle\?/ })).toHaveAttribute('aria-current', 'true'))
  })

  it('flags a verified discrepancy between sources', async () => {
    const api = setup(grounded({ discrepancy: true }))
    renderWithApi(<ChatView />, api.client)
    await ask('¿Altura del teckel?')
    expect(await screen.findByRole('note')).toHaveTextContent('discrepan')
  })
})
