import { test, expect } from '@playwright/test'
import { bootView, selectDag } from './fixtures/mock-backend'

// Validation gating is asserted at the network level (a blocked submit fires
// NO /workflow request) rather than against vjsf internals.

const WORKFLOW = '**/kaapana-backend/client/workflow'

test('valid form submits the exact conf_data payload (defaults + nested object)', async ({
  page,
}) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const req = await reqP
  expect(req.method()).toBe('POST')
  expect(req.postDataJSON()).toEqual({
    workflow_name: 'mock-all-fields',
    dag_id: 'mock-all-fields',
    instance_names: ['local-instance'],
    conf_data: {
      workflow_form: {
        text_field: 'hello',
        algorithm: 'alpha',
        enabled: false,
        threshold: 5,
        ratio: 0.5,
        tags: [],
        advanced: { retries: 3 },
      },
    },
    federated: false,
  })
})

test('a successful submit navigates the top window to the workflow list', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  // The wrapper redirects to the shell route /web/workflows/workflows on
  // @successful; no shell serves it here, so the fixture stubs it.
  await page.waitForURL('**/workflows/workflows')
})

test('edited values are reflected in the submitted payload', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  await page.getByLabel('Text Field').fill('edited')
  await page.getByRole('checkbox', { name: 'Enabled' }).check()
  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data.workflow_form
  expect(conf.text_field).toBe('edited')
  expect(conf.enabled).toBe(true)
})

test('required confirmation field blocks submit until accepted', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-confirmation')

  let fired = false
  page.on('request', (r) => {
    if (r.url().includes('/client/workflow')) fired = true
  })

  await page.getByRole('button', { name: 'Start Workflow' }).click()
  await expect(
    page.getByText('Please accept all required confirmations before starting the workflow.'),
  ).toBeVisible()
  expect(fired).toBe(false)

  await page.getByLabel('I accept the terms').check()
  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data.workflow_form
  expect(conf.confirmation).toBe(true)
})

test('clearing the required workflow name blocks submit with a field error', async ({
  page,
}) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')

  let fired = false
  page.on('request', (r) => {
    if (r.url().includes('/client/workflow')) fired = true
  })

  await page.getByLabel('Workflow name').fill('')
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  await expect(page.getByText('Workflow name is required')).toBeVisible()
  await page.waitForTimeout(300)
  expect(fired).toBe(false)
})

test('property-level `required: true` schema renders all fields and submits', async ({
  page,
}) => {
  // Regression: the real Kaapana convention puts boolean `required: true` on
  // properties; normalizeV2Schema must lift them into a parent-level array or
  // ajv rejects the schema ("required must be array") and the form blanks.
  const ajvErrors: string[] = []
  const capture = (t: string) => {
    if (/required must be array/.test(t)) ajvErrors.push(t)
  }
  page.on('pageerror', (e) => capture(e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') capture(m.text())
  })

  await bootView(page)
  await selectDag(page, 'validate-dicoms')

  await expect(page.getByRole('combobox', { name: 'Validator Algorithm' })).toHaveValue(
    'dicom-validator',
  )
  await expect(
    page.getByRole('checkbox', { name: 'Stop execution on Validation Error' }),
  ).toBeVisible()
  expect(ajvErrors).toEqual([])

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const body = (await reqP).postDataJSON()
  expect(body.conf_data).toEqual({
    workflow_form: {
      validator_algorithm: 'dicom-validator',
      exit_on_error: false,
    },
  })
})

test('empty required field blocks submit with a validation message and no request', async ({
  page,
}) => {
  await bootView(page)
  await selectDag(page, 'mock-required')

  let fired = false
  page.on('request', (r) => {
    if (r.url().includes('/client/workflow')) fired = true
  })

  await page.getByRole('button', { name: 'Start Workflow' }).click()
  await expect(page.getByText(/Validation of form input values failed!/)).toBeVisible()
  await page.waitForTimeout(300)
  expect(fired).toBe(false)
})

test('filling the required field unblocks submit and its value reaches the payload', async ({
  page,
}) => {
  await bootView(page)
  await selectDag(page, 'mock-required')

  await page.getByLabel('AE Title').fill('MY-AE')
  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data.workflow_form
  expect(conf.aetitle).toBe('MY-AE')
})

test('selecting a dataset reaches the payload as its object const (not a validation-blocked field)', async ({
  page,
}) => {
  // Regression: dataset_name declares type "string" while its oneOf consts are
  // objects; under vjsf 3 ajv rejects the selection and silently blocks submit.
  // normalizeV2Schema reconciles the type.
  await bootView(page)
  await selectDag(page, 'mock-dataset')

  const dsSelect = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await dsSelect.click()
  await page.getByRole('option', { name: 'nsclc (project) (42)' }).click()

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data
  expect(conf.data_form.dataset_name).toEqual({
    name: 'nsclc',
    username: 'kaapana',
    access_level: 'project',
  })
})

test('dataset limit defaults to "whole dataset": submit omits dataset_limit', async ({
  page,
}) => {
  // Omitting dataset_limit is the contract for "no limit" — the backend applies none.
  await bootView(page)
  await selectDag(page, 'mock-dataset')
  await expect(page.getByRole('checkbox', { name: 'Process whole dataset' })).toBeChecked()
  await expect(page.getByLabel('Limit dataset size')).toHaveCount(0)

  const dsSelect = page.locator('.v-autocomplete', { hasText: 'Dataset name (size)' })
  await dsSelect.click()
  await page.getByRole('option', { name: 'nsclc (project) (42)' }).click()

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data
  expect(conf.data_form).not.toHaveProperty('dataset_limit')
})

test('dataset limit toggled off: a min-1 number input appears and its value is submitted', async ({
  page,
}) => {
  await bootView(page)
  await selectDag(page, 'mock-dataset')
  await page.getByRole('checkbox', { name: 'Process whole dataset' }).click()

  const num = page.getByLabel('Limit dataset size')
  await expect(num).toBeVisible()
  await expect(num).toHaveValue('1')
  await num.fill('-5')
  await num.blur()
  await expect(num).toHaveValue('1')
  await num.fill('25')
  await num.blur()

  const reqP = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data
  expect(conf.data_form.dataset_limit).toBe(25)
})

test('the dataset-limit row carries an (i) help icon revealing the schema description', async ({
  page,
}) => {
  await bootView(page)
  await selectDag(page, 'mock-dataset')
  const icon = page.locator('.d-flex .wfe-help-icon')
  await expect(icon).toBeVisible()
  await icon.hover()
  await expect(page.getByText('Limit dataset to this many cases.')).toBeVisible()
})

test('a failed submit does not carry a stale dataset_limit into the retry', async ({ page }) => {
  // Regression: submitWorkflow merges dataset_limit into formData.data_form and
  // a failed POST left it there, so a retry after toggling back to "whole
  // dataset" resent the stale limit; the lifted keys are cleared per merge.
  await bootView(page)
  await selectDag(page, 'mock-dataset')

  await page.getByRole('checkbox', { name: 'Process whole dataset' }).click()
  const num = page.getByLabel('Limit dataset size')
  await num.fill('25')
  await num.blur()

  // First submit fails; form state persists.
  await page.route(WORKFLOW, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  )
  const req1P = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  expect((await req1P).postDataJSON().conf_data.data_form.dataset_limit).toBe(25)
  await expect(page.getByText('An error occured during the workflow creation!')).toBeVisible()

  // Toggle back to "whole dataset", make the endpoint succeed, and resubmit.
  await page.getByRole('checkbox', { name: 'Process whole dataset' }).click()
  await page.route(WORKFLOW, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workflow_id: 'wf-1' }) }),
  )
  const req2P = page.waitForRequest(WORKFLOW)
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf2 = (await req2P).postDataJSON().conf_data
  expect(conf2.data_form).not.toHaveProperty('dataset_limit')
})

test('submit backend error surfaces an error notification', async ({ page }) => {
  await bootView(page)
  await page.route('**/kaapana-backend/client/workflow', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'nope' }) }),
  )
  await selectDag(page, 'mock-all-fields')
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  await expect(page.getByText('An error occured during the workflow creation!')).toBeVisible()
})
