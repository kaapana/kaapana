import { test, expect } from '@playwright/test'
import { boot, prime, settle, defaultMockData, TASKS_PATH, APPS_PATH } from './fixtures/mock-backend'

function row(page: import('@playwright/test').Page, name: string) {
  return page.locator('.v-list-item').filter({ hasText: name })
}

test('the Tasks route shows only workflow-triggered apps, with ready / pending / error affordances', async ({ page }) => {
  await boot(page, defaultMockData, TASKS_PATH)

  // Exact match: the panel title is a substring of the empty-state message
  // ("No applications requesting your input.").
  await expect(page.getByText('Applications requesting your input', { exact: true })).toBeVisible()

  // Ready -> "Open"; pending -> "Starting..."; error -> "Error".
  await expect(row(page, 'Segmentation Editor').getByRole('button', { name: 'Open' })).toBeVisible()
  await expect(
    row(page, 'Volume Viewer').getByRole('button', { name: 'Starting...' }),
  ).toBeVisible()
  await expect(row(page, 'Broken Tool').getByRole('button', { name: 'Error' })).toBeVisible()

  await expect(
    row(page, 'Segmentation Editor').getByRole('button', { name: 'Finish Interaction' }),
  ).toBeVisible()

  await expect(row(page, 'Segmentation Editor').getByText(/^Started /)).toBeVisible()

  // The project-wide app belongs to the Apps route, not here.
  await expect(page.getByText('JupyterLab')).toHaveCount(0)
})

test('the Apps route shows only the project-wide app, without a finish control', async ({
  page,
}) => {
  await boot(page, defaultMockData, APPS_PATH)

  const jupyter = row(page, 'JupyterLab')
  await expect(jupyter.getByRole('button', { name: 'Open' })).toBeVisible()
  // Project-wide apps are not workflow-triggered -> no finish button.
  await expect(jupyter.getByRole('button', { name: 'Finish Interaction' })).toHaveCount(0)

  // Workflow-triggered apps belong to the Tasks route, not here.
  await expect(page.getByText('Segmentation Editor')).toHaveCount(0)
})

test('shows the per-route empty-state message when there are no applications', async ({ page }) => {
  await boot(page, { ...defaultMockData, activeApplications: [] }, TASKS_PATH)

  await expect(page.getByText('No applications requesting your input.')).toBeVisible()
  // The empty state is distinct from a failed fetch: no error notification fires.
  await expect(page.getByText('Could not load applications')).toHaveCount(0)

  await page.goto(APPS_PATH)
  await expect(page.getByText('No applications installed.')).toBeVisible()
})

test('a failing backend surfaces an error notification (distinct from empty)', async ({ page }) => {
  await prime(page)
  // Override the list endpoint with a 500 (later route wins).
  await page.route(/\/kube-helm-api\/active-applications/, (r) =>
    r.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' }),
  )
  await settle(page)

  await expect(page.getByText('Could not load applications')).toBeVisible()
  // The list still renders (empty) rather than crashing the view.
  await expect(page.getByText('No applications requesting your input.')).toBeVisible()
})

// Regression: the router auth guard must proceed even when checkAuth fails, so
// the view still mounts instead of aborting the navigation into a blank page
// (the gateway is the real auth boundary in front of the iframe).
test('auth check failure still mounts the view', async ({ page }) => {
  await prime(page)
  // Fail both auth endpoints so it holds in dev (token file) and preview (oauth2 proxy).
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill({ status: 500, body: '' }))
  await page.goto(TASKS_PATH)
  await expect(page.getByText('Sort by:')).toBeVisible()
})

test('a failing project fetch surfaces an error notification and fetches no applications', async ({
  page,
}) => {
  const pageErrors: string[] = []
  const listRequests: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('request', (r) => {
    if (/kube-helm-api\/active-applications/.test(r.url())) listRequests.push(r.url())
  })

  await prime(page)
  // Admin realm role routes the project lookup to /aii/projects.
  await page.route('**/aii/projects', (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'boom' }),
    }),
  )
  await settle(page)

  await expect(page.getByText('Could not load the project')).toBeVisible()
  // Without a project id every application would be filtered out, so a failed
  // lookup must not render as an empty list.
  expect(listRequests).toEqual([])
  await expect(page.getByText('No applications requesting your input.')).toBeVisible()
  expect(pageErrors).toEqual([])
})
