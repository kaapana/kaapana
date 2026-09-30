import { expect, test, type Page } from '@playwright/test'
import { dialog, dismissWithEscape, story } from './fixtures/helpers'

const opener = (page: Page) => page.getByRole('button', { name: 'Open the details' })

async function openStory(page: Page, id: string) {
  await story(page, `library-errordetailsdialog--${id}`)
  await opener(page).focus()
  await page.keyboard.press('Enter')
  await expect(dialog(page)).toBeVisible()
}

test('copying puts the whole report on the clipboard', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await openStory(page, 'default')
  await dialog(page).getByRole('button', { name: 'Copy details' }).click()

  await expect(dialog(page).getByRole('button', { name: 'Copied' })).toBeVisible()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    [
      'Could not uninstall MITK Workbench.',
      'Status: 409 Conflict',
      'Request: POST /kube-helm-api/helm-delete-chart',
      'Backend message: Release mitk-workbench-abc123 is being upgraded, try again later',
      'Request ID: c1f3a2e4-7b1d-4a9e-9f2c-0d5e6a7b8c9d',
      'Error: Request failed with status code 409',
    ].join('\n'),
  )
})

test('a failure without a response shows only the fields it has', async ({ page }) => {
  await openStory(page, 'no-response')
  await expect(dialog(page).locator('dt')).toHaveText(['Request', 'Error'])
})

test('a failure without any detail says so and offers nothing to copy', async ({ page }) => {
  await openStory(page, 'no-detail')
  await expect(dialog(page)).toContainText('The failure carried no further detail.')
  await expect(dialog(page).getByRole('button', { name: 'Copy details' })).toHaveCount(0)
})

test('closing returns focus to the control that opened it', async ({ page }) => {
  await openStory(page, 'default')
  await expect(dialog(page).getByRole('button', { name: 'Close' })).toBeFocused()
  await dismissWithEscape(page)
  await expect(opener(page)).toBeFocused()
})
