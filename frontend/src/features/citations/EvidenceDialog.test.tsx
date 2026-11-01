import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { CitationSummary } from '../../api/types'
import { citationFixture, fakeApi, renderWithApi, type RecordedRequest } from '../../test/fakeApi'
import { CitationList } from './CitationList'

const detail = {
  ...citationFixture,
  answer_id: 'ans-1',
  excerpt: null,
  current_excerpt: 'El teckel es un perro tenaz.',
  snapshot_id: 'snap-1',
  page_start: 42,
  page_end: 43,
  snapshot_valid: true,
}

describe('citation evidence', () => {
  it('opens the cited fragment and navigates the cited page range', async () => {
    const api = fakeApi({
      'GET /citations/cit-1': detail,
      'GET /citations/cit-1/page': (request: RecordedRequest) => {
        const page = Number(new URL(request.url, 'http://x').searchParams.get('physical_page'))
        return { body: { id: `p${page}`, version_id: 'ver-1', physical_page: page, printed_page_label: null, extracted_text: `Texto de la página ${page}`, extraction_method: 'direct' } }
      },
    })
    renderWithApi(<CitationList citations={[citationFixture as CitationSummary]} />, api.client)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Ver evidencia de la cita 1/ }))
    const dialog = await screen.findByRole('dialog', { name: 'Evidencia citada' })
    expect(dialog).toHaveTextContent('El teckel es un perro tenaz.')
    expect(await screen.findByText('Texto de la página 42')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Página siguiente' }))
    expect(await screen.findByText('Texto de la página 43')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows the preserved citation when the source was withdrawn', async () => {
    const api = fakeApi({
      'GET /citations/cit-1': {
        ...detail,
        version_id: null,
        current_excerpt: null,
        excerpt: 'Extracto conservado',
        source_status: 'withdrawn',
      },
    })
    renderWithApi(
      <CitationList citations={[{ ...(citationFixture as CitationSummary), current_source_status: 'withdrawn' }]} />,
      api.client,
    )
    expect(screen.getByText('Retirada')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: /Ver evidencia/ }))
    expect(await screen.findByText('Extracto conservado')).toBeInTheDocument()
    expect(screen.getByText(/La fuente fue retirada de la biblioteca/)).toBeInTheDocument()
    expect(api.requests.some((request) => request.url.includes('/page'))).toBe(false)
  })
})
