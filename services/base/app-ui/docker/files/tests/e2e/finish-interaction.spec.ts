import { test, expect } from '@playwright/test'
import { boot, dialog, row } from './fixtures/mock-backend'

async function askToFinish(page: import('@playwright/test').Page, name: string) {
  await row(page, name).getByRole('button', { name: 'Finish Interaction' }).click()
  await expect(dialog(page)).toContainText(`Finish the interaction with “${name}”?`)
}

test('finishing an interaction posts the release name and removes the row', async ({ page }) => {
  await boot(page)
  await askToFinish(page, 'Segmentation Editor')

  const [request] = await Promise.all([
    page.waitForRequest(
      (r) => r.url().includes('/complete-active-application') && r.method() === 'POST',
    ),
    dialog(page).getByRole('button', { name: 'Finish interaction' }).click(),
  ])
  expect(request.postDataJSON()).toMatchObject({ release_name: 'seg-editor-1a2b' })

  // On success the app is dropped from the list (and kept out across polls).
  await expect(page.getByText('Segmentation Editor')).toHaveCount(0)
})

test('cancelling the confirmation sends nothing', async ({ page }) => {
  await boot(page)
  let posts = 0
  page.on('request', (r) => {
    if (r.url().includes('/complete-active-application')) posts += 1
  })

  await askToFinish(page, 'Segmentation Editor')
  await dialog(page).getByRole('button', { name: 'Cancel' }).click()

  await expect(dialog(page)).toBeHidden()
  await expect(row(page, 'Segmentation Editor')).toBeVisible()
  expect(posts).toBe(0)
})

test('the row is unavailable while its finish request runs', async ({ page }) => {
  await boot(page)
  let posts = 0
  let release = () => {}
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route(/\/kube-helm-api\/complete-active-application/, async (r) => {
    posts += 1
    await held
    return r.fallback()
  })

  await askToFinish(page, 'Segmentation Editor')
  await dialog(page).getByRole('button', { name: 'Finish interaction' }).click()

  const editor = row(page, 'Segmentation Editor')
  await expect(editor.getByRole('button', { name: 'Finish Interaction' })).toBeDisabled()
  await expect(editor.getByRole('button', { name: 'Open' })).toBeDisabled()
  // Forced, because being unclickable is the point: a second click must not
  // reach the endpoint.
  await editor.getByRole('button', { name: 'Finish Interaction' }).click({ force: true })

  release()
  await expect(page.getByText('Segmentation Editor')).toHaveCount(0)
  expect(posts).toBe(1)
})

test('a failing finish keeps the row and reports the failure with its details', async ({
  page,
}) => {
  await boot(page)
  await page.route(/\/kube-helm-api\/complete-active-application/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'helm uninstall failed' }),
    }),
  )

  await askToFinish(page, 'Segmentation Editor')
  await dialog(page).getByRole('button', { name: 'Finish interaction' }).click()

  const notification = page
    .locator('.vue-notification')
    .filter({ hasText: 'Could not finish the interaction' })
  await expect(notification).toContainText('Segmentation Editor')
  // The backend message stays out of the notification and behind the disclosure.
  await expect(notification).not.toContainText('helm uninstall failed')
  await expect(row(page, 'Segmentation Editor').getByRole('button', { name: 'Open' })).toBeEnabled()

  await notification.click()
  const details = dialog(page).filter({ hasText: 'Copy details' })
  await expect(details).toContainText('helm uninstall failed')
  await expect(details).toContainText(
    'POST /project/admin/kube-helm-api/complete-active-application',
  )
})
