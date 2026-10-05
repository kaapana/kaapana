import { test, expect } from '@playwright/test'
import {
  boot,
  prime,
  row,
  defaultMockData,
  TASKS_PATH,
  APPS_PATH,
  TASKS_TITLE,
} from './fixtures/mock-backend'

test('the Tasks route shows only workflow-triggered apps, with ready / pending / error affordances', async ({
  page,
}) => {
  await boot(page, defaultMockData, TASKS_PATH)

  await expect(page.getByRole('heading', { name: TASKS_TITLE })).toBeVisible()

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

test('the display-name annotation names the application', async ({ page }) => {
  await boot(page, {
    ...defaultMockData,
    activeApplications: [
      {
        ...defaultMockData.activeApplications[0],
        annotations: { 'kaapana.ai/display-name': 'MITK Workbench' },
      },
    ],
  })
  await expect(row(page, 'MITK Workbench')).toBeVisible()
})

test('an application without paths is left out', async ({ page }) => {
  await boot(page, {
    ...defaultMockData,
    activeApplications: [
      ...defaultMockData.activeApplications,
      {
        ...defaultMockData.activeApplications[0],
        release_name: 'no-path',
        name: 'Pathless',
        paths: [],
      },
    ],
  })
  await expect(row(page, 'Segmentation Editor')).toBeVisible()
  await expect(page.getByText('Pathless')).toHaveCount(0)
})

test('sorting by name and start date, in both directions', async ({ page }) => {
  const [a, b] = defaultMockData.activeApplications
  await boot(page, {
    ...defaultMockData,
    activeApplications: [
      { ...a, name: 'Alpha', created_at: '2026-07-21T10:00:00Z' },
      { ...b, name: 'Beta', created_at: '2026-07-20T10:00:00Z' },
    ],
  })
  const titles = page.locator('.v-list-item-title')

  await expect(titles).toHaveText(['Alpha', 'Beta'])
  await page.getByRole('button', { name: 'Sort descending' }).click()
  await expect(titles).toHaveText(['Beta', 'Alpha'])

  await page.getByRole('button', { name: 'Started' }).click()
  await expect(titles).toHaveText(['Alpha', 'Beta'])
  await page.getByRole('button', { name: 'Sort ascending' }).click()
  await expect(titles).toHaveText(['Beta', 'Alpha'])
})

// Regression: the router auth guard must proceed even when checkAuth fails, so
// the view still mounts instead of aborting the navigation into a blank page
// (the gateway is the real auth boundary in front of the iframe).
test('auth check failure still mounts the view', async ({ page }) => {
  await prime(page)
  // Fail both auth endpoints so it holds in dev (token file) and preview (oauth2 proxy).
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) =>
    r.fulfill({ status: 500, body: '' }),
  )
  await page.goto(TASKS_PATH)
  await expect(page.getByText('Sort by:')).toBeVisible()
})
