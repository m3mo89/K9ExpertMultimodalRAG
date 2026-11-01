import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { documentFixture, fakeApi, renderWithApi } from '../../test/fakeApi'
import { LibraryView } from './LibraryView'

describe('LibraryView', () => {
  it('lists active sources and reveals failed versions safely', async () => {
    const api = fakeApi({
      'GET /documents': [
        documentFixture,
        { ...documentFixture, id: 'doc-2', title: 'Guía retirada', status: 'deactivated' },
      ],
      'GET /documents/doc-1/versions': [
        {
          id: 'ver-2',
          content_hash: 'abcdef1234567890',
          source_filename: 'enciclopedia-v2.pdf',
          edition: '3',
          status: 'candidate',
          created_at: '2026-11-02T00:00:00Z',
          job_id: 'job-2',
          job_stage: 'error',
          job_attempt: 2,
          failed_stage: 'extracting',
          error_code: 'ingestion_failed',
          job_updated_at: '2026-11-02T00:00:00Z',
        },
      ],
    })
    renderWithApi(<LibraryView />, api.client)
    expect(await screen.findByText(documentFixture.title)).toBeInTheDocument()
    expect(screen.queryByText('Guía retirada')).not.toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByText('Historial de versiones'))
    expect(await screen.findByText('enciclopedia-v2.pdf')).toBeInTheDocument()
    expect(screen.getByText('extracting')).toBeInTheDocument()
    expect(screen.getByText('ingestion_failed')).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Estado'), 'all')
    expect(screen.getByText('Guía retirada')).toBeInTheDocument()
  })
})
