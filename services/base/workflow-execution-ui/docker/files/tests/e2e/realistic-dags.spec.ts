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

  const submit = page.getByRole('button', { name: 'Start Workflow' })
  await expect(submit).toBeDisabled()

  const ds = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await ds.click()
  await page.keyboard.type('ds-1234')
  await page.getByRole('option', { name: 'ds-1234 (project) (1234)', exact: true }).click()

  await expect(submit).toBeEnabled()
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

  // The notice is a sentence the backend put in a field title. It belongs next
  // to the form as an inline alert, not as the label of a disabled input.
  const notice = page.locator('.v-alert', { hasText: 'No tasks are available in this project!' })
  await expect(notice).toBeVisible()
  await expect(notice).toContainText('You first have to install a task with nnunet-install-model.')
  await expect(page.getByLabel('No tasks are available in this project!')).toHaveCount(0)
  // the dataset picker alongside the notice must survive too
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

// Real dags pin values the workflow controls itself (BOA's "Input modality",
// total-segmentator's "single execution"). vjsf renders those disabled, which
// alone does not say why.
test('a schema-readOnly field says why it cannot be edited', async ({ page }) => {
  await bootView(
    page,
    singleDagData('fixed-field', {
      workflow_form: {
        type: 'object',
        properties: {
          input: {
            title: 'Input modality',
            description: 'Expected input modality.',
            type: 'string',
            default: 'CT',
            readOnly: true,
          },
        },
      },
    }),
  )
  await selectDag(page, 'fixed-field')

  await expect(page.getByLabel('Input modality')).toBeDisabled()
  await expect(page.getByText('Fixed by this workflow.')).toBeVisible()
})
