import { test, expect } from '@playwright/test'
import { bootView, selectDag } from './fixtures/mock-backend'

// Pins processDefaultsFromSettings: settings.workflows overrides + hideOnUI.

test('schema defaults populate every field', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'mock-all-fields')
  await expect(page.getByLabel('Text Field')).toHaveValue('hello')
  await expect(page.getByRole('combobox', { name: 'Algorithm' })).toHaveValue('alpha')
  await expect(page.getByLabel('Threshold', { exact: true })).toHaveValue('5')
  await expect(page.getByLabel('Ratio')).toHaveValue('0.5')
  await expect(page.getByLabel('Retries')).toHaveValue('3')
})

test('settings.workflows overrides the schema default for a field', async ({ page }) => {
  await bootView(page)
  await selectDag(page, 'settings-demo')
  await expect(page.getByRole('combobox', { name: 'Validator Algorithm' })).toHaveValue(
    'dciodvfy',
  )
})

test('hideOnUI hides the field but its default still reaches the payload', async ({
  page,
}) => {
  // hideOnUI marks the field x-display "hidden" (layout "none" in v2compat):
  // not rendered, but its default must still reach the submitted model.
  await bootView(page)
  await selectDag(page, 'settings-demo')
  await expect(page.getByRole('combobox', { name: 'Validator Algorithm' })).toHaveValue(
    'dciodvfy',
  )
  await expect(page.getByLabel('Tags Whitelist')).toHaveCount(0)

  const reqP = page.waitForRequest('**/kaapana-backend/client/workflow')
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  const conf = (await reqP).postDataJSON().conf_data.workflow_form
  expect(conf.tags_whitelist).toEqual([])
  expect(conf.validator_algorithm).toBe('dciodvfy')
})
