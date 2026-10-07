import { test, expect } from '@playwright/test'
import {
  dialog,
  openRunForm,
  openWorkflows,
  pressEscapeUntil,
  recordShellMessages,
  toasts,
} from './fixtures/helpers'

test.describe('run form', () => {
  test('starts a run with the chosen parameters and reports success', async ({ page }) => {
    const recorder = await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')

    await form.getByRole('combobox', { name: 'Dataset' }).click()
    await page.getByRole('option', { name: 'lung-ct' }).click()
    await form.getByRole('button', { name: 'Start workflow' }).click()

    await expect(form).toBeHidden()
    await expect(toasts(page)).toContainText('Workflow run started')
    expect(recorder.createdRuns).toHaveLength(1)
    const created = recorder.createdRuns[0]
    expect(created.workflow).toEqual({ id: 'segmentation-2', increment: 2 })
    expect(created.cleanup_policy).toBe('on_success')
    const values = Object.fromEntries(
      created.workflow_parameters!.map((p) => [p.env_variable_name, p.ui_form.default]),
    )
    expect(values).toEqual({ DATASET: 'lung-ct', THRESHOLD: 5, FORMAT: null })
  })

  test('selecting the success notification opens the runs entry of the shell', async ({ page }) => {
    await openWorkflows(page)
    await page.route('**/web/**', (r) =>
      r.fulfill({ contentType: 'text/html', body: '<p>shell</p>' }),
    )
    const form = await openRunForm(page, 'Segmentation')
    await form.getByRole('combobox', { name: 'Dataset' }).click()
    await page.getByRole('option', { name: 'lung-ct' }).click()
    await form.getByRole('button', { name: 'Start workflow' }).click()

    await toasts(page).filter({ hasText: 'Workflow run started' }).click()
    await expect(page).toHaveURL(/\/web\/experimental\/workflow-runs-v2$/)
  })

  test('validation explains what to fix and blocks the submission', async ({ page }) => {
    const recorder = await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')

    await form.getByRole('spinbutton', { name: 'Threshold' }).fill('42')
    await form.getByRole('button', { name: 'Start workflow' }).click()

    await expect(form).toContainText('Select dataset.')
    await expect(form).toContainText('Enter a whole number between 1 and 10.')
    expect(recorder.createdRuns).toHaveLength(0)
  })

  test('required fields carry no asterisk; optional ones say so', async ({ page }) => {
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    await expect(form.getByRole('combobox', { name: 'Dataset', exact: true })).toBeVisible()
    await expect(form.getByRole('combobox', { name: 'Format (optional)' })).toBeVisible()
    await expect(form).not.toContainText('*')
  })

  test('a failed start keeps the form open and explains the failure', async ({ page }) => {
    const recorder = await openWorkflows(page, {
      routes: (p) =>
        p.route('**/workflow-api/v1/workflow-runs', (r) =>
          r.request().method() === 'POST'
            ? r.fulfill({
                status: 409,
                contentType: 'application/json',
                body: '{"detail":"Dataset is locked."}',
              })
            : r.fallback(),
        ),
    })
    const form = await openRunForm(page, 'Segmentation')
    await form.getByRole('combobox', { name: 'Dataset' }).click()
    await page.getByRole('option', { name: 'lung-ct' }).click()
    await form.getByRole('button', { name: 'Start workflow' }).click()

    const error = form.getByTestId('submit-error')
    await expect(error).toContainText('The workflow run could not be created. Dataset is locked.')
    await error.getByRole('button', { name: 'Details' }).click()
    await expect(page.getByRole('dialog').filter({ hasText: 'Copy details' })).toContainText('409')
    expect(recorder.createdRuns).toHaveLength(0)
  })

  test('a dataset load failure is shown at the field with a retry', async ({ page }) => {
    let fail = true
    await openWorkflows(page, {
      routes: (p) =>
        p.route('**/kaapana-backend/client/datasets*', (r) =>
          fail ? r.fulfill({ status: 500 }) : r.fallback(),
        ),
    })
    const form = await openRunForm(page, 'Segmentation')
    await expect(form).toContainText('The datasets could not be loaded.')
    fail = false
    await form.getByRole('button', { name: 'Try again' }).click()
    await expect(form).not.toContainText('The datasets could not be loaded.')
  })

  test('help texts are reachable by keyboard', async ({ page }) => {
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    const help = form.getByRole('button', { name: 'Field help' })
    await help.focus()
    await expect(page.getByRole('tooltip')).toContainText('Higher values keep fewer voxels.')
  })
})

test.describe('unsaved changes in the run form', () => {
  test('an untouched form closes without asking', async ({ page }) => {
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    await form.getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog(page)).toHaveCount(0)
  })

  test('closing an edited form asks first, and keeping it keeps the values', async ({ page }) => {
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    await form.getByRole('spinbutton', { name: 'Threshold' }).fill('7')

    await pressEscapeUntil(page, async () => (await page.getByText('Discard changes?').count()) > 0)
    const confirm = dialog(page).filter({ hasText: 'Discard changes?' })
    await expect(confirm.getByRole('button', { name: 'Keep editing' })).toBeFocused()
    await confirm.getByRole('button', { name: 'Keep editing' }).click()

    await expect(form.getByRole('spinbutton', { name: 'Threshold' })).toHaveValue('7')
  })

  test('discarding resets the form to its defaults', async ({ page }) => {
    await openWorkflows(page)
    let form = await openRunForm(page, 'Segmentation')
    await form.getByRole('spinbutton', { name: 'Threshold' }).fill('7')
    await form.getByRole('button', { name: 'Cancel' }).click()
    await dialog(page)
      .filter({ hasText: 'Discard changes?' })
      .getByRole('button', { name: 'Discard changes' })
      .click()
    await expect(dialog(page)).toHaveCount(0)

    form = await openRunForm(page, 'Segmentation')
    await expect(form.getByRole('spinbutton', { name: 'Threshold' })).toHaveValue('5')
  })

  test('the shell is told while the form holds unsaved changes', async ({ page }) => {
    const messages = await recordShellMessages(page)
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    await form.getByRole('spinbutton', { name: 'Threshold' }).fill('7')
    await expect.poll(messages).toContainEqual({ type: 'kaapana:view-dirty', dirty: true })

    await form.getByRole('spinbutton', { name: 'Threshold' }).fill('5')
    await expect
      .poll(async () => (await messages()).at(-1))
      .toEqual({ type: 'kaapana:view-dirty', dirty: false })
  })
})
