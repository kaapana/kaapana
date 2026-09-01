import { test, expect } from '@playwright/test'
import { boot } from './fixtures/mock-backend'

function row(page: import('@playwright/test').Page, name: string) {
  return page.locator('.v-list-item').filter({ hasText: name })
}

test('finishing an interaction posts the release name and removes the row', async ({ page }) => {
  await boot(page)

  await row(page, 'Segmentation Editor').getByRole('button', { name: 'Finish Interaction' }).click()
  await expect(page.getByText('Finish interaction?')).toBeVisible()

  const [request] = await Promise.all([
    page.waitForRequest(
      (r) => r.url().includes('/complete-active-application') && r.method() === 'POST',
    ),
    page.getByRole('button', { name: 'Yes' }).click(),
  ])
  expect(request.postDataJSON()).toMatchObject({ release_name: 'seg-editor-1a2b' })

  // On success the app is dropped from the list (and kept out across polls).
  await expect(page.getByText('Segmentation Editor')).toHaveCount(0)
})

test('a failing finish request surfaces an error dialog', async ({ page }) => {
  await boot(page)

  // Make the finish call fail (later route wins over the fixture's 200).
  await page.route(/\/kube-helm-api\/complete-active-application/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'helm uninstall failed' }),
    }),
  )

  await row(page, 'Segmentation Editor').getByRole('button', { name: 'Finish Interaction' }).click()
  await page.getByRole('button', { name: 'Yes' }).click()

  await expect(page.getByText('Could not finish interaction', { exact: true })).toBeVisible()
  await expect(page.getByText(/helm uninstall failed/)).toBeVisible()
  // The app stays in the list since the finish did not complete.
  await expect(row(page, 'Segmentation Editor').getByRole('button', { name: 'Open' })).toBeVisible()
})
