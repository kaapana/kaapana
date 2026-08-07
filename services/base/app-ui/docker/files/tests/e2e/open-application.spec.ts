import { test, expect } from '@playwright/test'
import { boot, openedUrls, projectPath } from './fixtures/mock-backend'

function row(page: import('@playwright/test').Page, name: string) {
  return page.locator('.v-list-item').filter({ hasText: name })
}

test('a ready app opens its path in a new tab without a dialog', async ({ page }) => {
  await boot(page)

  await row(page, 'Segmentation Editor').getByRole('button', { name: 'Open' }).click()

  await expect.poll(() => openedUrls(page)).toContain(projectPath('seg-editor-1a2b'))
  // Ready apps skip the status dialog.
  await expect(page.getByText('Application is ready')).toHaveCount(0)
})

test('a pending app shows the "starting" dialog and can be visited anyway', async ({ page }) => {
  await boot(page)

  await row(page, 'Volume Viewer').getByRole('button', { name: 'Starting...' }).click()

  await expect(page.getByText('Application is starting')).toBeVisible()
  await expect(page.getByText(/Volume Viewer.*still starting/)).toBeVisible()

  await page.getByRole('button', { name: 'Visit anyway' }).click()

  await expect.poll(() => openedUrls(page)).toContain(projectPath('vol-viewer-3c4d'))
  await expect(page.getByText('Application is starting')).toBeHidden()
})

test('an errored app shows the problem dialog with pod detail', async ({ page }) => {
  await boot(page)

  await row(page, 'Broken Tool').getByRole('button', { name: 'Error' }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Problem starting the application')).toBeVisible()
  // The offending pod is surfaced verbatim in the dialog (also shown in the row tooltip).
  await expect(dialog.getByText('app-pod-0: CrashLoopBackOff (0/1, restarts: 7)')).toBeVisible()
})
