import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { mockApi } from './mockApi.ts'

const views = [
  { hash: '#/analizar', heading: 'Encuentra tu perro de caza ideal' },
  { hash: '#/consultar', heading: 'Consultar la biblioteca' },
  { hash: '#/biblioteca', heading: 'Biblioteca de conocimiento' },
  { hash: '#/administracion', heading: 'Administración' },
  { hash: '#/sistema', heading: 'Sistema' },
]

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(0)
}

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(results.violations.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([])
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

for (const view of views) {
  test(`${view.hash} fits the viewport and passes WCAG checks`, async ({ page }) => {
    await page.goto(`/${view.hash}`)
    await expect(page.getByRole('heading', { level: 1, name: view.heading })).toBeAttached()
    await expect(page.getByRole('navigation', { name: 'Principal' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await expectAccessible(page)
  })
}

test('navigation links are reachable touch targets', async ({ page }) => {
  await page.goto('/')
  for (const link of await page.getByRole('navigation', { name: 'Principal' }).getByRole('link').all()) {
    const box = await link.boundingBox()
    expect(box?.height).toBeGreaterThanOrEqual(44)
  }
})

test('the default view completes a BreedMatch analysis without chat', async ({ page }) => {
  const requests: string[] = []
  page.on('request', (request) => requests.push(new URL(request.url()).pathname))
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1, name: 'Encuentra tu perro de caza ideal' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Análisis de razas' })).toHaveAttribute('aria-current', 'page')
  await page.getByRole('button', { name: 'pelo duro' }).click()
  await page.getByRole('button', { name: 'Analizar razas' }).click()
  const report = page.getByRole('region', { name: 'Informe de análisis' })
  await expect(report.getByRole('table', { name: 'Comparación por criterio' })).toBeVisible()
  await expect(report.getByText('No documentado').first()).toBeVisible()
  await report.getByText('Teckel alemán', { exact: true }).last().click()
  await expect(report.getByText(/pág\. 40 \(PDF 42\)/)).toBeVisible()
  await report.getByRole('button', { name: 'Ver ficha de Teckel alemán' }).first().click()
  const sheet = page.getByRole('dialog', { name: 'Teckel alemán' })
  await expect(sheet.getByText(/descienden de antiguos perros/)).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await expectAccessible(page)
  await page.keyboard.press('Escape')
  await report.getByRole('button', { name: 'Útil', exact: true }).click()
  await report.getByRole('button', { name: 'Enviar valoración' }).click()
  await expect(report.getByText(/su valoración quedó registrada/)).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await expectAccessible(page)
  expect(requests.filter((path) => /\/api\/v1\/(queries|conversations)/.test(path))).toEqual([])
})

test('guided recommendation completes, compares results and remains accessible', async ({ page }) => {
  await page.goto('/#/analizar')
  for (const label of ['Venado', 'Seguir un rastro', 'Monte denso']) {
    await page.getByRole('button', { name: label }).click()
    await page.getByRole('button', { name: /Continuar|Revisar perfil/ }).click()
  }
  await expect(page.getByRole('form', { name: 'Resumen del perfil' })).toBeVisible()
  await page.getByRole('button', { name: 'Ver recomendaciones' }).click()
  const results = page.getByRole('region', { name: 'Recomendaciones' })
  await expect(results.getByText('Teckel alemán').first()).toBeVisible()
  await page.getByLabel('Comparar Teckel alemán').check()
  await page.getByLabel('Comparar Basset hound').check()
  await expect(page.getByRole('table', { name: 'Comparación de 2 razas' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await expectAccessible(page)
})

test('a question, its citation and its evidence work at this viewport', async ({ page }) => {
  await page.goto('/#/consultar')
  await page.getByLabel('Pregunta').fill('¿Cómo es el teckel?')
  await page.getByRole('button', { name: 'Preguntar' }).click()
  await expect(page.getByText(/el teckel es un perro tenaz y valiente, criado/)).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await expectAccessible(page)

  await page.getByRole('button', { name: /Ver evidencia de la cita 1/ }).click()
  const dialog = page.getByRole('dialog', { name: 'Evidencia citada' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('pág. 40 (PDF 42)')).toBeVisible()
  await expect(dialog.locator('.page-text')).toContainText('TECKEL')
  await expectAccessible(page)
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
})

test('system view distinguishes degraded and unavailable components', async ({ page }) => {
  await page.goto('/#/sistema')
  await page.getByLabel('Secreto administrativo').fill('secret')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByText('Estado general:')).toContainText('Degradado')
  await expect(page.locator('.component-unavailable')).toContainText('Modelos locales')
  await expect(page.locator('.component-degraded')).toContainText('Trabajador de ingesta')
  await expectNoHorizontalOverflow(page)
  await expectAccessible(page)
})

test('keyboard users can skip to content', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Keyboard navigation is checked on desktop.')
  await page.goto('/')
  await page.keyboard.press('Tab')
  const skip = page.getByRole('link', { name: 'Saltar al contenido' })
  await expect(skip).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main')).toBeFocused()
})
