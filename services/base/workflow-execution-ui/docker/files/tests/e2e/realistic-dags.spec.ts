import { test, expect } from '@playwright/test'
import {
  bootView,
  selectDag,
  singleDagData,
  largeDatasetSchema,
  noModelsSchema,
  emptyUploadSchema,
} from './fixtures/mock-backend'

// Regression coverage: real backend DAG shapes that crashed vjsf 3 and blanked
// the execution form (fixtures in fixtures/mock-backend.ts).

const WORKFLOW = '**/kaapana-backend/client/workflow'

test('large dataset list (1500) renders a searchable picker and submits the object const', async ({
  page,
}) => {
  // The dataset picker is rendered natively (Vuetify autocomplete) because
  // vjsf 3 overflows the render stack building one node per oneOf branch.
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await bootView(page, singleDagData('big-dataset', largeDatasetSchema(2400)))
  await selectDag(page, 'big-dataset')

  // workflow_form field renders -> the form is not blanked
  await expect(page.getByText('Single execution')).toBeVisible()

  const ds = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await expect(ds).toBeVisible()
  await ds.click()
  await page.keyboard.type('ds-1234')
  await page.getByRole('option', { name: 'ds-1234 (project) (1234)', exact: true }).click()

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data
  expect(conf.data_form.dataset_name).toEqual({
    name: 'ds-1234',
    username: 'kaapana',
    access_level: 'project',
  })
  expect(pageErrors).toHaveLength(0)
})

test('required dataset blocks submit until one is chosen (large list)', async ({ page }) => {
  await bootView(page, singleDagData('big-dataset', largeDatasetSchema(2400)))
  await selectDag(page, 'big-dataset')
  let fired = false
  page.on('request', (r) => { if (r.url().includes('/client/workflow')) fired = true })
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  await page.waitForTimeout(500)
  expect(fired).toBe(false)
  await expect(page.getByText('Dataset name is required')).toBeVisible()
})

test('nnunet "no models installed" (empty oneOf) renders the notice instead of blanking', async ({
  page,
}) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  const consoleErrors: string[] = []
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })

  await bootView(page, singleDagData('no-models', noModelsSchema))
  await selectDag(page, 'no-models')

  // the dataset picker alongside the notice must survive too
  await expect(page.getByText('No tasks are available in this project!').first()).toBeVisible()
  await expect(page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })).toBeVisible()
  expect(pageErrors).toHaveLength(0)
  expect(consoleErrors.join('\n')).not.toContain('non-empty array')
})

test('empty upload list (empty enum) renders the field instead of failing schema compile', async ({
  page,
}) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  const consoleErrors: string[] = []
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })

  await bootView(page, singleDagData('empty-upload', emptyUploadSchema))
  await selectDag(page, 'empty-upload')

  await expect(page.getByText('Objects from uploads directory').first()).toBeVisible()
  expect(pageErrors).toHaveLength(0)
  expect(consoleErrors.join('\n')).not.toContain('non-empty array')
})
