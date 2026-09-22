import { test, expect, type Page } from '@playwright/test'
import {
  countRequests,
  dialog,
  HELM,
  openView,
  pressEscapeUntil,
  recordShellMessages,
  row,
} from './fixtures/helpers'

// The configuration form is the view's only editable state, so it carries the
// "Unsaved changes" and "Validation" rules of the design guidelines.

async function openForm(page: Page) {
  await row(page, 'nnU-Net Training').getByRole('button', { name: 'Install' }).click()
  await expect(dialog(page)).toBeVisible()
  return dialog(page)
}

async function openEditedForm(page: Page) {
  const form = await openForm(page)
  await form.getByRole('textbox', { name: /Workflow name/ }).fill('half-typed-run')
  return form
}

test.describe('unsaved changes', () => {
  test('closing an edited form asks first, and Keep editing resumes it', async ({ page }) => {
    await openView(page)
    await openEditedForm(page)

    await pressEscapeUntil(page, () => page.getByText(/Discard the configuration/).isVisible())
    await expect(page.getByText(/Discard the configuration for nnU-Net Training/)).toBeVisible()

    await page.getByRole('button', { name: 'Keep editing', exact: true }).click()
    await expect(dialog(page).getByRole('textbox', { name: /Workflow name/ })).toHaveValue(
      'half-typed-run',
    )
  })

  test('an unedited form closes without asking', async ({ page }) => {
    await openView(page)
    await openForm(page)

    await pressEscapeUntil(page, () => dialog(page).isHidden())

    await expect(dialog(page)).toHaveCount(0)
    await expect(page.getByText(/Discard the configuration/)).toHaveCount(0)
  })

  test('an edited form reports the view dirty to the shell, and discarding clears it', async ({
    page,
  }) => {
    const messages = await recordShellMessages(page)
    const dirtyStates = async () =>
      (await messages()).filter((m) => m.type === 'kaapana:view-dirty').map((m: any) => m.dirty)
    await openView(page)

    await openEditedForm(page)
    await expect.poll(dirtyStates).toContain(true)

    await pressEscapeUntil(page, () => page.getByText(/Discard the configuration/).isVisible())
    await page.getByRole('button', { name: 'Discard changes', exact: true }).click()
    await expect.poll(async () => (await dirtyStates()).at(-1)).toBe(false)
    await expect(dialog(page)).toHaveCount(0)
  })

  test('submitting clears the dirty state', async ({ page }) => {
    const messages = await recordShellMessages(page)
    await openView(page)

    const form = await openEditedForm(page)
    await form.getByRole('button', { name: 'Install', exact: true }).click()

    await expect
      .poll(async () => (await messages()).filter((m) => m.type === 'kaapana:view-dirty').at(-1))
      .toEqual({ type: 'kaapana:view-dirty', dirty: false })
  })
})

test.describe('fields', () => {
  test.beforeEach(({ page }) => openView(page))

  test('a required field left empty says what to enter, and nothing is sent', async ({ page }) => {
    const installs = countRequests(page, HELM.install)
    const form = await openForm(page)
    await form.getByRole('textbox', { name: /Workflow name/ }).fill('')

    await form.getByRole('button', { name: 'Install', exact: true }).click()

    await expect(form.getByText('Enter a value for Workflow name (workflow_name).')).toBeVisible()
    await expect(form).toBeVisible()
    expect(installs()).toBe(0)
  })

  test('field help is a focusable, named control', async ({ page }) => {
    const form = await openForm(page)
    const help = form.getByRole('button', { name: 'Field help' })
    await expect(help).toBeVisible()

    // Reach it as a keyboard user does: the tooltip opens on :focus-visible,
    // which programmatic focus() does not produce.
    await form.getByRole('textbox', { name: /Workflow name/ }).click()
    for (let i = 0; i < 4 && !(await help.evaluate((el) => el === document.activeElement)); i++) {
      await page.keyboard.press('Tab')
    }

    await expect(help).toBeFocused()
    await expect(page.getByText('Shown in the workflow list once the training starts.')).toBeVisible()
  })
})
