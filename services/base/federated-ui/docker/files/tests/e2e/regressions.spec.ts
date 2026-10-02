import { test, expect, type Locator } from '@playwright/test'
import { installMockBackend, seedShellState, VIEW_PATH } from './fixtures/mock-backend'
import { card, openView } from './fixtures/helpers'

type Box = { x: number; y: number; width: number; height: number }

function sameRow(a: Box, b: Box) {
  return a.y < b.y + b.height && b.y < a.y + a.height
}

async function box(loc: Locator): Promise<Box> {
  const b = await loc.boundingBox()
  if (!b) throw new Error('element has no bounding box')
  return b
}

test('the card header keeps its controls on the title row at a narrow width', async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 900 })
  await openView(page)

  for (const name of ['central-node', 'gpu-node-1']) {
    const header = card(page, name).locator('.v-card-item').first()
    const title = await box(header.locator('.v-card-title'))
    const buttons = header.locator('button')
    const count = await buttons.count()
    expect(count).toBeGreaterThan(0)
    for (let i = 0; i < count; i++) {
      const b = await box(buttons.nth(i))
      expect(sameRow(b, title), `button ${i} on ${name} wrapped off the title row`).toBe(true)
      expect(Math.abs(b.width - b.height), `button ${i} on ${name} is not square`).toBeLessThanOrEqual(1)
    }
  }
})

test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })

  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('heading', { name: 'Instance overview' })).toBeVisible()
  await expect(card(page, 'central-node')).toBeVisible()
  expect(pageErrors).toEqual([])
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

test('auth check failure still mounts the view', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill({ status: 500, body: '' }))
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: 'Instance overview' })).toBeVisible()
})

test('sets the document title', async ({ page }) => {
  await openView(page)
  await expect(page).toHaveTitle('Instance overview')
})
