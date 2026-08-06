import { test, expect, type Locator } from '@playwright/test'
import { installMockBackend, seedShellState, VIEW_PATH } from './fixtures/mock-backend'

type Box = { x: number; y: number; width: number; height: number }

// Two boxes share a horizontal band, i.e. they sit on the same visual row.
function sameRow(a: Box, b: Box) {
  return a.y < b.y + b.height && b.y < a.y + a.height
}
function intersects(a: Box, b: Box) {
  return !(
    a.x + a.width <= b.x ||
    b.x + b.width <= a.x ||
    a.y + a.height <= b.y ||
    b.y + b.height <= a.y
  )
}
async function box(loc: Locator): Promise<Box> {
  const b = await loc.boundingBox()
  if (!b) throw new Error('element has no bounding box')
  return b
}

// Regression: the header's fixed cols="9" name column made the type icon and
// action buttons wrap below a clipped heading at narrow widths (Vuetify 3
// v-row wraps by default); it is now a non-wrapping flex row.
test('instance card header stays on one row at a narrow width', async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 900 })
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: central-node')).toBeVisible()

  // Both cards: the local one (home icon + copy button) and the remote one
  // (cloud icon + status dot + delete button) wrap at different points.
  for (const name of ['central-node', 'gpu-node-1']) {
    const card = page
      .getByText(`Instance name: ${name}`)
      .locator('xpath=ancestor::*[contains(concat(" ", @class, " "), " v-card ")][1]')
    const title = card.locator('.v-card-title')
    const heading = await box(card.getByText(`Instance name: ${name}`))

    // No wrap: every header control (type icon, status dot, action buttons)
    // shares the heading's row.
    const controls = title.locator('.v-icon, button')
    const n = await controls.count()
    expect(n).toBeGreaterThan(0)
    for (let i = 0; i < n; i++) {
      expect(
        sameRow(await box(controls.nth(i)), heading),
        `control ${i} on ${name} wrapped off the header row`,
      ).toBe(true)
    }

    // Icon buttons stay square (a fixed narrow column would squeeze them oval),
    // and none overlaps the heading text.
    const buttons = title.locator('button')
    const bn = await buttons.count()
    expect(bn).toBeGreaterThan(0)
    for (let i = 0; i < bn; i++) {
      const b = await box(buttons.nth(i))
      expect(Math.abs(b.width - b.height), `button ${i} on ${name} is not square`).toBeLessThanOrEqual(1)
      expect(intersects(b, heading), `button ${i} on ${name} overlaps the heading`).toBe(false)
    }
  }
})

// Regression class that blanked data-gallery-ui: an unguarded JSON.parse of the
// shell-owned localStorage["settings"] in App.vue's setup throws before the
// root renders. Every other spec seeds it, so boot WITHOUT seedShellState.
test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })

  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Instance Overview')).toBeVisible()
  await expect(page.getByText('Instance name: central-node')).toBeVisible()
  expect(pageErrors).toEqual([])
  // Vue routes a throw from setup() to console.error, never window.onerror.
  // Match the error NAME — the message wording is engine-version specific.
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

// Regression: the router auth guard must proceed even when checkAuth fails, so
// the view still mounts instead of hanging on a swallowed rejection (the gateway
// is the real auth boundary in front of the iframe).
test('auth check failure still mounts the view', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Fail both auth endpoints so it holds in dev (token file) and preview (oauth2 proxy).
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill({ status: 500, body: '' }))
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance Overview')).toBeVisible()
})
