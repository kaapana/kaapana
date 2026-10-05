import { test, expect } from '@playwright/test'
import {
  boot,
  defaultMockData,
  dialog,
  openedUrls,
  poll,
  projectPath,
  readyPod,
  row,
} from './fixtures/mock-backend'

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

  await page.getByRole('button', { name: 'Open anyway' }).click()

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

test('an open status dialog follows the application to ready', async ({ page }) => {
  const data = structuredClone(defaultMockData)
  await boot(page, data)

  await row(page, 'Volume Viewer').getByRole('button', { name: 'Starting...' }).click()
  await expect(dialog(page).getByText('Application is starting')).toBeVisible()

  data.activeApplications[1].pods = [readyPod]
  await poll(page)

  await expect(dialog(page).getByText('Application is ready')).toBeVisible()
  await dialog(page).getByRole('button', { name: 'Open', exact: true }).click()
  await expect.poll(() => openedUrls(page)).toContain(projectPath('vol-viewer-3c4d'))
})
