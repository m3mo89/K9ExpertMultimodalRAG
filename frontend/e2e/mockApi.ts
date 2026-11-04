import type { Page, Route } from '@playwright/test'
import { analysisFixture, configurationFixture, profileFixture } from '../src/test/breedMatchFixture.ts'

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
  'GET /configuration': configurationFixture,
  'GET /breeds': [
    { name: 'Basset hound', group: 'Sabuesos de talla pequeña', fragment_count: 6 },
    { name: 'Teckel alemán', group: null, fragment_count: 9 },
  ],
  'GET /breeds/Teckel%20alem%C3%A1n/profile': profileFixture,
  'POST /breed-analyses': analysisFixture,
  'POST /breed-analyses/an-1/feedback': {
    id: 'f-1', analysis_id: 'an-1', trace_id: 'trace-9', useful: 1, comment: null, created_at: 't',
  },
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

const v2Routes: Record<string, unknown> = {
  'POST /hunter-profiles/validate': {
    schema_version: '2.0', translator_version: 'hunter-profile-v1', completeness: 'complete',
    missing_fields: [], constraints: [], dimensions: [
      { key: 'prey', values: ['venado'], weight: 0.3, required: true },
      { key: 'modality', values: ['rastreo'], weight: 0.3, required: true },
      { key: 'terrain', values: ['monte_denso'], weight: 0.25, required: true },
      { key: 'experience', values: ['principiante'], weight: 0.2, required: true },
      { key: 'daily_availability', values: ['1_2h'], weight: 0.15, required: true },
    ],
  },
  'POST /recommendations': {
    schema_version: '2.0', recommendation_id: 'r-1', status: 'completed', policy_version: 'v2',
    snapshot_id: 'snap-1', trace_id: 'trace-r', summary: null,
    limitations: ['fewer_supported_candidates'], candidates: [
      { breed: 'Teckel alemán', band: 'high', compatibility: 1, coverage: 0.7, penalties: [], excluded: false,
        dimensions: [{ key: 'modality', compatibility: 1, documented: true, conflicting: false, evidence_ids: ['frag-1'] }] },
      { breed: 'Basset hound', band: 'moderate', compatibility: 0.6, coverage: 0.6, penalties: [], excluded: false,
        dimensions: [{ key: 'modality', compatibility: null, documented: true, conflicting: true, evidence_ids: ['frag-2'] }] },
    ],
  },
  'GET /breeds/Teckel%20alem%C3%A1n/structured-profile': {
    breed: 'Teckel alemán', snapshot_id: 'snap-1', policy_version: 'v1', attributes: [],
  },
  'GET /breeds/Basset%20hound/structured-profile': {
    breed: 'Basset hound', snapshot_id: 'snap-1', policy_version: 'v1', attributes: [],
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
  await page.route('**/api/v2/**', async (route: Route) => {
    const url = new URL(route.request().url())
    const key = `${route.request().method()} ${url.pathname.replace('/api/v2', '')}`
    const body = v2Routes[key]
    if (body === undefined) {
      await route.fulfill({ status: 404, json: { code: 'not_mocked', message: key, details: null, trace_id: 't', retryable: false } })
      return
    }
    await route.fulfill({ status: 200, json: body })
  })
}
