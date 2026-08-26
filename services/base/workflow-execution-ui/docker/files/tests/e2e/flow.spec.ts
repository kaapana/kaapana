import { test, expect } from '@playwright/test'
import {
  bootView,
  selectDag,
  workflowField,
  installMockBackend,
  seedShellState,
  defaultMockData,
  VIEW_PATH,
} from './fixtures/mock-backend'

test('boots and renders the execution card', async ({ page }) => {
  await bootView(page)
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
  // Single local instance -> the multi-instance runner select is not rendered.
  await expect(page.getByText('Runner instances')).toHaveCount(0)
})

test('DAG select lists every available workflow', async ({ page }) => {
  await bootView(page)
  await workflowField(page).click()
  const options = page.getByRole('option')
  await expect(options).toHaveText([
    'mock-all-fields',
    'settings-demo',
    'mock-confirmation',
    'mock-dataset',
    'mock-conditional',
    'mock-documented',
    'validate-dicoms',
    'mock-required',
  ])
})

test('the Workflow field is a type-to-filter autocomplete showing a plain name (no chip)', async ({
  page,
}) => {
  await bootView(page)
  const field = workflowField(page)
  await field.click()
  await field.fill('conditional')
  await expect(page.getByRole('option')).toHaveText(['mock-conditional'])
  await page.getByRole('option', { name: 'mock-conditional', exact: true }).click()
  await expect(field).toHaveValue('mock-conditional')
  await expect(page.locator('.v-autocomplete .v-chip')).toHaveCount(0)
})

test('native fields expose a discreet (i) help icon that reveals help on hover', async ({
  page,
}) => {
  await bootView(page)
  const icon = page.locator('.wfe-help-icon').first()
  await expect(icon).toBeVisible()
  await icon.hover()
  await expect(page.getByText('Workflow to execute')).toBeVisible()
})

test('selecting a DAG reveals its form and auto-fills the workflow name', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  await expect(page.getByLabel('Workflow name')).toHaveValue('mock-all-fields')
  await expect(page.getByLabel('Text Field')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start Workflow' })).toBeVisible()
})

test('Clear resets the selected workflow and hides its form', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  await expect(page.getByLabel('Text Field')).toBeVisible()
  await page.getByRole('button', { name: 'Clear', exact: true }).click()
  await expect(page.getByLabel('Text Field')).toHaveCount(0)
})

test('dataset selection renders the oneOf select with its options', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-dataset')
  const dsSelect = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await expect(dsSelect).toBeVisible()
  await dsSelect.click()
  await expect(page.getByRole('option')).toHaveText([
    'nsclc (project) (42)',
    'brains (project) (7)',
  ])
  await page.getByRole('option', { name: 'nsclc (project) (42)' }).click()
  await expect(page.getByRole('combobox', { name: 'Dataset name (size)' })).toHaveValue(
    /nsclc/,
  )
})

test('boots without a seeded localStorage["settings"] (no JSON.parse crash)', async ({
  page,
}) => {
  // Regression: an unguarded JSON.parse(localStorage["settings"]) threw in
  // onMounted when the shell had not seeded the key. The flow below still
  // completes regardless, so only the console assertion at the end can see it.
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await workflowField(page).waitFor({ state: 'visible' })

  await selectDag(page, 'mock-dataset')
  const dsSelect = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await expect(dsSelect).toBeVisible()
  await dsSelect.click()
  await page.getByRole('option', { name: 'nsclc (project) (42)' }).click()
  await expect(page.getByRole('combobox', { name: 'Dataset name (size)' })).toHaveValue(/nsclc/)
  expect(pageErrors).toHaveLength(0)
  // Vue routes a throw inside onMounted to console.error, never window.onerror.
  // Match the error NAME — the message wording is engine-version specific.
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

test('documentation_form renders a docs link instead of a form', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-documented')
  const link = page.getByRole('link', { name: 'Link to the documentation' })
  await expect(link).toBeVisible()
  await expect(link).toHaveAttribute('href', /\/docs\/.*airflow\.html/)
  // the workflow_form field alongside the doc link still renders
  await expect(page.getByLabel('Receiver port')).toBeVisible()
})

test('empty state: no available DAGs shows a loading spinner, no Start button', async ({
  page,
}) => {
  // No dags -> the DAG select never renders (a spinner takes its place), so
  // bootView's wait for it would hang; boot manually instead.
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, dags: [] })
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
  await expect(page.locator('.v-progress-circular')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start Workflow' })).toHaveCount(0)
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
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
})

test('backend error on get-dags: view still boots, no DAG select', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.route('**/kaapana-backend/client/get-dags', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
  await expect(page.locator('.v-progress-circular')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start Workflow' })).toHaveCount(0)
})
