import type { Page, Route } from '@playwright/test'

const document = {
  id: 'doc-1',
  title: 'Enciclopedia de perros de caza',
  author: 'Autor',
  category: 'caza',
  status: 'active',
  active_version_id: 'ver-1',
  edition: '2',
  updated_at: '2026-11-01T00:00:00+00:00',
}

const citation = {
  id: 'cit-1',
  fragment_id: 'frag-1',
  document_id: 'doc-1',
  version_id: 'ver-1',
  title: document.title,
  author: 'Autor',
  edition: '2',
  physical_page: 42,
  printed_page_label: '40',
  source_status: 'active',
}

const routes: Record<string, unknown> = {
  'GET /health': { status: 'ok', worker_concurrency: 1 },
  'GET /documents': [document],
  'GET /documents/doc-1/versions': [
    {
      id: 'ver-1',
      content_hash: 'abcdef1234567890',
      source_filename: 'enciclopedia.pdf',
      edition: '2',
      status: 'active',
      created_at: '2026-11-01T00:00:00Z',
      job_id: 'job-1',
      job_stage: 'available',
      job_attempt: 1,
      failed_stage: null,
      error_code: null,
      job_updated_at: '2026-11-01T00:00:00Z',
    },
  ],
  'GET /conversations': [{ id: 'conv-0', title: '¿Origen del beagle?', created_at: 't', updated_at: '2026-11-01T00:00:00Z' }],
  'POST /conversations': { id: 'conv-1', created_at: 't', updated_at: 't', messages: [] },
  'POST /queries': {
    query_id: 'q-1',
    answer_id: 'ans-1',
    status: 'grounded',
    answer: 'Según la enciclopedia, el teckel es un perro tenaz y valiente, criado para la caza bajo tierra.',
    snapshot_id: 'snap-1',
    reason: null,
    citations: [citation],
    conversation_id: 'conv-1',
  },
  'GET /citations/cit-1': {
    ...citation,
    answer_id: 'ans-1',
    excerpt: null,
    current_excerpt: 'El teckel es un perro tenaz y valiente.',
    snapshot_id: 'snap-1',
    page_start: 42,
    page_end: 42,
    snapshot_valid: true,
  },
  'GET /citations/cit-1/page': {
    id: 'p-42',
    version_id: 'ver-1',
    physical_page: 42,
    printed_page_label: '40',
    extracted_text: 'TECKEL\nEl teckel es un perro tenaz y valiente.',
    extraction_method: 'direct',
  },
  'GET /admin/health': {
    status: 'degraded',
    checked_at: '2026-11-01T00:00:00Z',
    components: {
      api: { status: 'ok', detail: 'serving' },
      database: { status: 'ok', detail: 'schema_current' },
      worker: { status: 'degraded', detail: 'worker_heartbeat_stale' },
      inference: { status: 'unavailable', detail: 'inference_unreachable' },
    },
  },
  'GET /admin/metrics': {
    generated_at: '2026-11-01T00:00:00Z',
    queries: { grounded: 3, abstained: 1 },
    documents: { active: 1 },
    jobs: { available: 1 },
    feedback: { useful: 2, not_useful: 1 },
  },
}

/** Serves the application API from fixtures so browser tests need no backend or models. */
export async function mockApi(page: Page) {
  await page.route('**/api/v1/**', async (route: Route) => {
    const url = new URL(route.request().url())
    const key = `${route.request().method()} ${url.pathname.replace('/api/v1', '')}`
    const body = routes[key]
    if (body === undefined) {
      await route.fulfill({ status: 404, json: { code: 'not_mocked', message: key, details: null, trace_id: 't', retryable: false } })
      return
    }
    await route.fulfill({ status: 200, json: body })
  })
}
