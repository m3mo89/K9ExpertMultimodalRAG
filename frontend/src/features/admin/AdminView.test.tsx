import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { documentFixture, errorBody, fakeApi, renderWithApi } from '../../test/fakeApi'
import { AdminView } from './AdminView'

const health = { status: 'ok', checked_at: 't', components: {} }

async function signIn(secret = 'secret') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Secreto administrativo'), secret)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
  return user
}

describe('AdminView', () => {
  it('rejects an invalid administrative secret', async () => {
    const api = fakeApi({ 'GET /admin/health': { status: 401, body: errorBody('admin_unauthorized') } })
    renderWithApi(<AdminView />, api.client)
    await signIn('wrong')
    expect(await screen.findByRole('alert')).toHaveTextContent('Credencial administrativa no válida.')
  })

  it('deletes only after a version-bound confirmation', async () => {
    const api = fakeApi({
      'GET /admin/health': health,
      'GET /documents': [documentFixture],
      'POST /admin/confirmations': { token: 'tok-1', expires_at: '2026-11-01T00:05:00Z' },
      'DELETE /documents/doc-1': { document_id: 'doc-1', snapshot_id: 's', status: 'deleted' },
    })
    renderWithApi(<AdminView />, api.client)
    const user = await signIn()
    await user.click(await screen.findByRole('button', { name: 'Eliminar…' }))
    const remove = await screen.findByRole('button', { name: 'Eliminar documento' })
    expect(remove).toBeDisabled()
    await user.click(screen.getByRole('checkbox', { name: /no se puede deshacer/ }))
    await user.click(remove)
    expect(await screen.findByText(/retirado de nuevas consultas/)).toBeInTheDocument()

    const confirmation = api.requests.find((request) => request.url.endsWith('/admin/confirmations'))
    expect(confirmation?.body).toEqual({
      resource_id: 'doc-1',
      operation: 'delete',
      resource_version: documentFixture.updated_at,
    })
    const deletion = api.requests.find((request) => request.method === 'DELETE')
    expect(deletion?.body).toEqual({ confirmation_token: 'tok-1', resource_version: documentFixture.updated_at })
    expect(deletion?.headers).toMatchObject({ 'X-K9-Admin-Secret': 'secret' })
  })

  it('surfaces a stale confirmation instead of deleting', async () => {
    const api = fakeApi({
      'GET /admin/health': health,
      'GET /documents': [documentFixture],
      'POST /admin/confirmations': { token: 'tok-1', expires_at: 't' },
      'DELETE /documents/doc-1': { status: 409, body: errorBody('stale_resource_version') },
    })
    renderWithApi(<AdminView />, api.client)
    const user = await signIn()
    await user.click(await screen.findByRole('button', { name: 'Eliminar…' }))
    await user.click(await screen.findByRole('checkbox', { name: /no se puede deshacer/ }))
    await user.click(screen.getByRole('button', { name: 'Eliminar documento' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El documento cambió')
  })

  it('uploads a PDF and polls its ingestion job until it finishes', async () => {
    let polls = 0
    const api = fakeApi({
      'GET /admin/health': health,
      'GET /documents': [],
      'POST /documents': { status: 202, body: { document_id: 'doc-2', version_id: 'v', job_id: 'job-1', status: 'received' } },
      'GET /jobs/job-1': () => {
        polls += 1
        return { body: { id: 'job-1', version_id: 'v', stage: polls === 1 ? 'extracting' : 'available', attempt: 1, error_code: null } }
      },
    })
    renderWithApi(<AdminView />, api.client)
    const user = await signIn()
    const file = new File(['%PDF-1.7'], 'teckel.pdf', { type: 'application/pdf' })
    await user.upload(await screen.findByLabelText('Archivo PDF'), file)
    await user.type(screen.getByLabelText('Título'), 'Teckel')
    await user.click(screen.getByRole('button', { name: 'Subir y procesar' }))
    expect(await screen.findByText('Extrayendo texto')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Disponible')).toBeInTheDocument(), { timeout: 4000 })
    const upload = api.requests.find((request) => request.method === 'POST' && request.url === '/api/v1/documents')
    expect(upload?.body).toBeInstanceOf(FormData)
    expect((upload!.body as FormData).get('title')).toBe('Teckel')
  })

  it('reindexes a document and shows request progress', async () => {
    const progress = { request_id: 'r-1', scope: 'document', document_id: 'doc-1', total: 1, failed: 0, jobs: [] }
    const api = fakeApi({
      'GET /admin/health': health,
      'GET /documents': [documentFixture],
      'POST /documents/doc-1/reindex': { status: 202, body: { ...progress, state: 'queued', completed: 0 } },
      'GET /admin/reindex/r-1': { ...progress, state: 'completed', completed: 1 },
    })
    renderWithApi(<AdminView />, api.client)
    const user = await signIn()
    await user.click(await screen.findByRole('button', { name: 'Reindexar' }))
    expect(await screen.findByText('Completada')).toBeInTheDocument()
  })
})
