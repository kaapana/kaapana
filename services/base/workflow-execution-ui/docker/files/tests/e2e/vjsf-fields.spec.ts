import { test, expect } from '@playwright/test'
import { bootView, selectDag } from './fixtures/mock-backend'

// Schema -> form rendering for every vjsf field kind the real DAG schemas use,
// packed into the mock-all-fields fixture. Pins the vjsf 2 -> 3 migration.

test.beforeEach(async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
})

test('string field renders as a text input with its schema default', async ({ page }) => {
  await expect(page.getByLabel('Text Field')).toHaveValue('hello')
})

test('a field description is revealed by a discreet (i) help toggle', async ({ page }) => {
  // useDescription: ['subtitle','help'] renders vjsf 3's own (i) help toggle.
  const toggle = page.locator('.vjsf-help-message-toggle').first()
  await expect(toggle).toBeVisible()
  await expect(page.getByText('The text to process')).toHaveCount(0)
  await toggle.click()
  await expect(page.getByText('The text to process')).toBeVisible()
})

test('enum field renders as a select with the schema default selected', async ({ page }) => {
  const select = page.getByRole('combobox', { name: 'Algorithm' })
  await expect(select).toHaveValue('alpha')
  await page.locator('.v-select', { hasText: 'Algorithm' }).click()
  await expect(page.getByRole('option')).toHaveText(['alpha', 'beta', 'gamma'])
})

test('boolean field renders as a checkbox reflecting the default', async ({ page }) => {
  await expect(page.getByRole('checkbox', { name: 'Enabled' })).not.toBeChecked()
})

test('integer field renders as a number input with the default', async ({ page }) => {
  await expect(page.getByLabel('Threshold', { exact: true })).toHaveValue('5')
})

test('number field renders as a number input with the fractional default', async ({ page }) => {
  await expect(page.getByLabel('Ratio')).toHaveValue('0.5')
})

test('array field renders as a chips input', async ({ page }) => {
  await expect(page.getByLabel('Tags')).toBeVisible()
})

test('nested object field renders as a subsection with its own fields', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'Advanced' })).toBeVisible()
  await expect(page.getByLabel('Retries')).toHaveValue('3')
})

test('dependent (conditional) field appears when its trigger is set and reaches the payload', async ({
  page,
}) => {
  // normalizeV2Schema rewrites draft-07 `dependencies` into allOf/if/then
  // because json-layout never gates `dependencies` branches on the trigger.
  await selectDag(page, 'mock-conditional')
  await expect(page.getByLabel('Extra Param')).toHaveCount(0)

  await page.locator('.v-select', { hasText: 'Mode' }).click()
  await page.getByRole('option', { name: 'advanced', exact: true }).click()
  await expect(page.getByRole('combobox', { name: 'Mode' })).toHaveValue('advanced')

  await expect(page.getByLabel('Extra Param')).toBeVisible()
  await page.getByLabel('Extra Param').fill('deep')

  const reqP = page.waitForRequest('**/kaapana-backend/client/workflow')
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data.workflow_form
  expect(conf.mode).toBe('advanced')
  expect(conf.extra_param).toBe('deep')
})

test('editing fields updates the rendered values', async ({ page }) => {
  await page.getByLabel('Text Field').fill('changed')
  await expect(page.getByLabel('Text Field')).toHaveValue('changed')

  const enabled = page.getByRole('checkbox', { name: 'Enabled' })
  await enabled.check()
  await expect(enabled).toBeChecked()
})
