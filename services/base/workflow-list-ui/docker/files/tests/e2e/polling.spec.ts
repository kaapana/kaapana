import { test, expect } from '@playwright/test'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('auto-refreshes the workflow list on the polling interval', async ({ page }) => {
  await page.clock.install()
  const data = { ...defaultMockData }
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('running-wf', { exact: true })).toBeVisible()

  // Backend data changes between polls; the route handler reads `data` at
  // request time, so the next poll serves the renamed workflow.
  data.workflows = data.workflows.map((w) =>
    w.workflow_name === 'running-wf' ? { ...w, workflow_name: 'refreshed-wf' } : w,
  )

  const req = page.waitForRequest(
    (r) =>
      /\/kaapana-backend\/client\/workflows(\?|$)/.test(r.url()) && r.method() === 'GET',
  )
  await page.clock.runFor(15_000)
  await req
  await expect(page.getByText('refreshed-wf', { exact: true })).toBeVisible()
})

// Regression: the 15s background poll must refresh silently. It used to fire a
// success toast whenever the (default empty) search box was blank, so the toast
// popped every 15s. The toast is now reserved for an explicit user refresh.
test('the background poll refreshes without a success toast', async ({ page }) => {
  await page.clock.install()
  const data = { ...defaultMockData }
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('running-wf', { exact: true })).toBeVisible()

  // Rename between polls so we can await the poll result rendering — proving the
  // fetch .then ran (where the stray toast used to fire) before asserting silence.
  data.workflows = data.workflows.map((w) =>
    w.workflow_name === 'running-wf' ? { ...w, workflow_name: 'polled-wf' } : w,
  )
  const req = page.waitForRequest(
    (r) =>
      /\/kaapana-backend\/client\/workflows(\?|$)/.test(r.url()) && r.method() === 'GET',
  )
  await page.clock.runFor(15_000)
  await req
  await expect(page.getByText('polled-wf', { exact: true })).toBeVisible()
  await expect(page.getByText('Successfully refreshed workflow list.')).toHaveCount(0)
})

// Counterpart: the poll fix must not silence the user-facing refresh toast.
test('an explicit refresh click still fires the success toast', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Workflow List', { exact: true })).toBeVisible()

  await page.locator('.v-card-title button:has(.mdi-refresh)').click()
  await expect(page.getByText('Successfully refreshed workflow list.')).toBeVisible()
})
