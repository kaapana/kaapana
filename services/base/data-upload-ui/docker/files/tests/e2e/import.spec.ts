import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  defaultMockData,
  datasetImportData,
  DATASET_IMPORT_DAG,
  VIEW_PATH,
} from './fixtures/mock-backend'

const IMPORT_DAG = defaultMockData.dags[0]
const WORKFLOW = '**/kaapana-backend/client/workflow'

async function openImportDialog(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: /Import the data/ }).click()
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
}

test('import dialog loads the import workflow and submits it', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await openImportDialog(page)

  // The single import dag + its matching schema auto-select, filling the
  // workflow name and revealing the submit action.
  await expect(page.getByLabel('Workflow name')).toHaveValue(IMPORT_DAG)
  const startBtn = page.getByRole('button', { name: 'Start Workflow' })
  await expect(startBtn).toBeVisible()

  const workflowReq = page.waitForRequest(
    (r) => r.url().includes('/kaapana-backend/client/workflow') && r.method() === 'POST',
  )
  await startBtn.click()

  const req = await workflowReq
  const body = req.postDataJSON()
  expect(body.dag_id).toBe(IMPORT_DAG)
  expect(body.workflow_name).toBe(IMPORT_DAG)
  expect(body.instance_names).toEqual(['kaapana-local'])
  expect(body.conf_data).toHaveProperty('workflow_form')

  await expect(page.getByText('Workflow successfully created!')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeHidden()
})

test('a failing workflow submission surfaces an error and keeps the dialog open', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/kaapana-backend/client/workflow', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'nope' }) }),
  )
  await page.goto(VIEW_PATH)
  await openImportDialog(page)

  await expect(page.getByLabel('Workflow name')).toHaveValue(IMPORT_DAG)
  await page.getByRole('button', { name: 'Start Workflow' }).click()

  await expect(page.getByText('An error occured during the workflow creation!')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
})

test('cancelling the import dialog closes it without submitting', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await openImportDialog(page)

  await expect(page.getByRole('button', { name: 'Start Workflow' })).toBeVisible()
  await page.getByRole('button', { name: 'Cancel' }).click()
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeHidden()
})

test('a data_form dag: dataset lift renders natively and the selection is submitted', async ({
  page,
}) => {
  // The synced rescue lifts dataset_name out of vjsf into a native autocomplete;
  // its selected object const must reach conf_data.data_form.dataset_name. The
  // limit toggle defaults to "whole dataset", so dataset_limit is omitted.
  await installMockBackend(page, datasetImportData())
  await page.goto(VIEW_PATH)
  await openImportDialog(page)
  await expect(page.getByLabel('Workflow name')).toHaveValue(DATASET_IMPORT_DAG)

  const dsSelect = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await expect(dsSelect).toBeVisible()
  await dsSelect.click()
  await page.getByRole('option', { name: 'nsclc (project) (42)' }).click()

  await expect(page.getByRole('checkbox', { name: 'Process whole dataset' })).toBeChecked()

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data
  expect(conf.data_form.dataset_name).toEqual({
    name: 'nsclc',
    username: 'kaapana',
    access_level: 'project',
  })
  expect(conf.data_form).not.toHaveProperty('dataset_limit')
})

test('a data_form dag: toggling the limit off submits a min-1 dataset_limit', async ({
  page,
}) => {
  await installMockBackend(page, datasetImportData())
  await page.goto(VIEW_PATH)
  await openImportDialog(page)

  await page.getByRole('checkbox', { name: 'Process whole dataset' }).click()
  const num = page.getByLabel('Limit dataset size')
  await expect(num).toBeVisible()
  await num.fill('-3')
  await num.blur()
  await expect(num).toHaveValue('1')
  await num.fill('10')
  await num.blur()

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data
  expect(conf.data_form.dataset_limit).toBe(10)
})

test('a failed submit does not carry a stale dataset_limit into the retry', async ({ page }) => {
  // Regression: a failed POST leaves the merged data_form in place, so toggling
  // back to "whole dataset" and resubmitting must NOT resend the old limit.
  await installMockBackend(page, datasetImportData())
  await page.goto(VIEW_PATH)
  await openImportDialog(page)

  await page.getByRole('checkbox', { name: 'Process whole dataset' }).click()
  const num = page.getByLabel('Limit dataset size')
  await num.fill('25')
  await num.blur()

  await page.route(WORKFLOW, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  )
  const req1P = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  expect((await req1P).postDataJSON().conf_data.data_form.dataset_limit).toBe(25)
  await expect(page.getByText('An error occured during the workflow creation!')).toBeVisible()

  await page.getByRole('checkbox', { name: 'Process whole dataset' }).click()
  await page.route(WORKFLOW, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workflow_id: 'wf-1' }) }),
  )
  const req2P = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf2 = (await req2P).postDataJSON().conf_data
  expect(conf2.data_form).not.toHaveProperty('dataset_limit')
})
