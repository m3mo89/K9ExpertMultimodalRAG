import { expect, test } from '@playwright/test'
import { mockApi } from './mockApi.ts'

// Addresses of internal services that must never be reachable from, or known to, the browser.
const forbidden = [/11434/, /ollama/i, /chroma/i, /:8000\b/, /127\.0\.0\.1:(?!5174)/, /localhost:(?!5174)/]

test('the browser only talks to the same-origin application API', async ({ page, baseURL }) => {
  const origin = new URL(baseURL!).origin
  const requests: string[] = []
  const scripts: Promise<string>[] = []
  page.on('request', (request) => requests.push(request.url()))
  page.on('response', (response) => {
    if (response.request().resourceType() === 'script') scripts.push(response.text())
  })
  await mockApi(page)

  // Exercise every view and the main user and administrator flows.
  await page.goto('/#/consultar')
  await page.getByLabel('Pregunta').fill('¿Cómo es el teckel?')
  await page.getByRole('button', { name: 'Preguntar' }).click()
  await page.getByRole('button', { name: /Ver evidencia de la cita 1/ }).click()
  await expect(page.locator('.page-text')).toContainText('TECKEL')
  await page.keyboard.press('Escape')
  await page.goto('/#/biblioteca')
  await page.getByText('Historial de versiones', { exact: true }).click()
  await expect(page.getByText('enciclopedia.pdf')).toBeVisible()
  await page.goto('/#/sistema')
  await page.getByLabel('Secreto administrativo').fill('secret')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByText('Estado general:')).toBeVisible()

  const apiCalls = requests.filter((url) => new URL(url).pathname.startsWith('/api/'))
  expect(apiCalls.length).toBeGreaterThan(5)
  for (const url of requests) {
    const parsed = new URL(url)
    if (parsed.protocol === 'data:') continue
    expect(parsed.origin, url).toBe(origin)
    if (parsed.pathname.startsWith('/api/')) expect(parsed.pathname, url).toMatch(/^\/api\/v1\//)
    for (const pattern of forbidden) expect(url, url).not.toMatch(pattern)
  }

  // The shipped code must not even know internal model or index addresses.
  for (const source of await Promise.all(scripts)) {
    for (const pattern of [/11434/, /ollama/i, /chromadb/i]) expect(source).not.toMatch(pattern)
  }
})
