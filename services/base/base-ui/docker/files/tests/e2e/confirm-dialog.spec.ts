import { expect, test, type Page } from '@playwright/test'
import { dialog, dismissWithEscape, story } from './fixtures/helpers'

// ConfirmDialog, driven through its "Destructive" story: the safe action takes
// the initial focus, every way out that is not Confirm is a cancel, and focus
// returns to the control that opened the dialog.

const opener = (page: Page) => page.getByRole('button', { name: 'Open confirmation' })
const outcome = (page: Page) => page.getByTestId('confirm-outcome')

async function openByKeyboard(page: Page) {
  await opener(page).focus()
  await page.keyboard.press('Enter')
  await expect(dialog(page)).toBeVisible()
}

test.beforeEach(async ({ page }) => {
  await story(page, 'library-confirmdialog--destructive')
  await expect(opener(page)).toBeVisible()
})

test('opening puts the initial focus on Cancel, so Enter never confirms', async ({ page }) => {
  await openByKeyboard(page)
  await expect(dialog(page).getByRole('button', { name: 'Cancel' })).toBeFocused()

  await page.keyboard.press('Enter')
  await expect(dialog(page)).toBeHidden()
  await expect(outcome(page)).toHaveText('Last outcome: cancel')
})

test('Cancel closes the dialog as a cancel and returns focus to the opener', async ({ page }) => {
  await openByKeyboard(page)
  await dialog(page).getByRole('button', { name: 'Cancel' }).click()

  await expect(dialog(page)).toBeHidden()
  await expect(outcome(page)).toHaveText('Last outcome: cancel')
  await expect(opener(page)).toBeFocused()
})

test('Escape closes the dialog as a cancel and returns focus to the opener', async ({ page }) => {
  await openByKeyboard(page)
  await dismissWithEscape(page)

  await expect(outcome(page)).toHaveText('Last outcome: cancel')
  await expect(opener(page)).toBeFocused()
})

test('Confirm closes the dialog as a confirm', async ({ page }) => {
  await openByKeyboard(page)
  await dialog(page).getByRole('button', { name: 'Delete workflow' }).click()

  await expect(dialog(page)).toBeHidden()
  await expect(outcome(page)).toHaveText('Last outcome: confirm')
})
