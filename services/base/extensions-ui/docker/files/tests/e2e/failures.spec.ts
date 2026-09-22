import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'
import { collectPageErrors, failRoute, HELM, openView, row, serverError } from './fixtures/helpers'

test('a failed uninstall notifies and leaves the row installed', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, {
    routes: (p) => failRoute(p, HELM.uninstall, 'Chart uninstall failed: release is locked'),
  })

  await row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()

  await expect(page.getByText('Uninstall failed', { exact: true })).toBeVisible()
  await expect(page.getByText('release is locked')).toBeVisible()
  // The extension is still deployed, so the row must keep offering Uninstall.
  await expect(row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a failed marketplace refresh notifies and keeps the list', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, {
    routes: (p) => failRoute(p, HELM.update, 'helm repo update failed'),
  })

  await page.getByTestId('update-extensions').click()

  await expect(page.getByText('Refresh failed', { exact: true })).toBeVisible()
  await expect(page.getByText('helm repo update failed')).toBeVisible()
  await expect(row(page, 'MITK Workbench')).toBeVisible()
  expect(pageErrors).toEqual([])
})

// An aborted request leaves the axios error without a `response`.
test('an unreachable import-container notifies instead of throwing', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, {
    routes: (p) => p.route(`**${HELM.importContainer}*`, (r) => r.abort()),
  })

  await page.locator('input.filepond--browser').setInputFiles({
    name: 'container.tar',
    mimeType: 'application/x-tar',
    buffer: Buffer.from('mock container'),
  })

  await expect(page.getByText('Import failed', { exact: true })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a failed project lookup notifies instead of rejecting unhandled', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  // The list is scoped by the document URL, so it still loads.
  await openView(page, undefined, {
    routes: (p) => failRoute(p, '/aii/projects', 'project lookup failed'),
  })

  await expect(page.getByText('Project unavailable', { exact: true })).toBeVisible()
  await expect(page.getByText('project lookup failed')).toBeVisible()
  expect(pageErrors).toEqual([])
})

// The store's catch is the only thing keeping getCommonData's rejection off the page.
test('a failed commonData load leaves the view working', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await installMockBackend(page)
  await page.route('**/jsons/commonData.json', (r) => r.fulfill(serverError('commonData missing')))
  await page.goto(VIEW_PATH)

  await expect(row(page, 'MITK Workbench')).toBeVisible()
  expect(pageErrors).toEqual([])
})
