import { test, expect } from '@playwright/test'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('renders the workflow list with a mix of states', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Workflow List', { exact: true })).toBeVisible()
  for (const wf of defaultMockData.workflows) {
    await expect(page.getByText(wf.workflow_name, { exact: true })).toBeVisible()
  }
  await expect(page.getByText('wf-running-001')).toBeVisible()
  await expect(page.getByText('ct-scans(public)')).toBeVisible()
})

test('status column shows per-state job counts', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  // running-wf has workflow_jobs ['running','running','finished'] -> a chip '2'
  // (running) and a chip '1' (finished) in its status cell.
  const runningRow = page.getByRole('row').filter({ hasText: 'running-wf' })
  await expect(runningRow.getByRole('button', { name: '2', exact: true })).toBeVisible()
  await expect(runningRow.getByRole('button', { name: '1', exact: true })).toBeVisible()

  // failed-wf: ['failed','finished'] -> two chips of '1'
  const failedRow = page.getByRole('row').filter({ hasText: 'failed-wf' })
  await expect(failedRow.getByRole('button', { name: '1', exact: true }).first()).toBeVisible()
})

// Regression: a stray pa-6 pushed the toolbar icons ~10px below the square
// button's center. A square-only check would not catch it, so guard that the
// icon center matches the button center.
test('toolbar icon buttons render their glyph centered', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Workflow List', { exact: true })).toBeVisible()

  // Scoped to the card title: mdi-open-in-new also appears inside expanded-row
  // job tables, which would trip strict mode if a row were open.
  const toolbar = page.locator('.v-card-title')
  for (const icon of ['mdi-sync', 'mdi-open-in-new', 'mdi-refresh']) {
    const btn = await toolbar.locator(`button:has(.${icon})`).boundingBox()
    const glyph = await toolbar.locator(`.${icon}`).boundingBox()
    expect(btn, icon).not.toBeNull()
    expect(glyph, icon).not.toBeNull()
    if (!btn || !glyph) continue
    expect(Math.abs(btn.width - btn.height), `${icon} square`).toBeLessThan(1)
    const dx = glyph.x + glyph.width / 2 - (btn.x + btn.width / 2)
    const dy = glyph.y + glyph.height / 2 - (btn.y + btn.height / 2)
    expect(Math.abs(dx), `${icon} h-center`).toBeLessThan(1)
    expect(Math.abs(dy), `${icon} v-center`).toBeLessThan(1)
  }
})

test('renders an empty state when the backend returns no workflows', async ({ page }) => {
  await installMockBackend(page, { ...defaultMockData, workflows: [], totalWorkflows: 0 })
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Workflow List', { exact: true })).toBeVisible()
  await expect(page.getByText('No workflows yet.')).toBeVisible()
  await expect(page.getByText('running-wf', { exact: true })).toHaveCount(0)
})

// Regression class that blanked data-gallery-ui: an unguarded JSON.parse of the
// shell-owned localStorage["settings"] in App.vue's setup throws before the
// root renders. Every other spec gets the seed, so boot with it suppressed.
test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })

  await installMockBackend(page, defaultMockData, { seedSettings: false })
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Workflow List', { exact: true })).toBeVisible()
  await expect(page.getByText('running-wf', { exact: true })).toBeVisible()
  expect(pageErrors).toEqual([])
  // Vue routes a throw from setup() to console.error, never window.onerror.
  // Match the error NAME — the message wording is engine-version specific.
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

// Regression: the router auth guard must proceed even when checkAuth fails, so
// the view still mounts instead of aborting the navigation into a blank page
// (the gateway is the real auth boundary in front of the iframe).
test('auth check failure still mounts the view', async ({ page }) => {
  await installMockBackend(page)
  // Fail both auth endpoints so it holds in dev (token file) and preview (oauth2 proxy).
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill({ status: 500, body: '' }))
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Workflow List', { exact: true })).toBeVisible()
})

test('shows an error notification when the workflow fetch fails', async ({ page }) => {
  await installMockBackend(page)
  await page.route(/\/kaapana-backend\/client\/workflows(\?|$)/, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' }),
  )
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Error while refreshing workflow list.')).toBeVisible()
  await expect(page.getByText('running-wf', { exact: true })).toHaveCount(0)
})

// Regression: expanding a workflow that has no jobs left the table spinning
// forever and re-raised its warning on every 15s poll, because the job fetch
// ran as a side effect of a computed and only cleared `loading` on a non-empty
// response.
test('a workflow without jobs settles and warns once, not on every refresh', async ({ page }) => {
  await installMockBackend(page, { ...defaultMockData, jobs: [] })

  // The "has this workflow any jobs at all?" probe is the limit=1 request.
  const probes: string[] = []
  page.on('request', (r) => {
    if (/\/client\/jobs\?/.test(r.url()) && r.url().includes('limit=1')) probes.push(r.url())
  })

  await page.goto(VIEW_PATH)
  await page.getByText('running-wf', { exact: true }).click()

  await expect(page.getByText('No jobs for workflow running-wf')).toBeVisible()
  await expect(page.getByText('Request is processed - wait a few seconds.')).toBeHidden()
  expect(probes).toHaveLength(1)

  // A list refresh re-fetches the expanded row's jobs but must not probe again.
  await page.locator('.v-card-title button:has(.mdi-refresh)').click()
  await expect(page.getByText('Successfully refreshed workflow list.')).toBeVisible()
  await expect(page.getByText('Request is processed - wait a few seconds.')).toBeHidden()
  expect(probes).toHaveLength(1)
})
