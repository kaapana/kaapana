import { test, expect, type Page } from '@playwright/test'
import { confirmAction, installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

// kube-helm and aii raise FastAPI HTTPExceptions, so a failure body is {detail}.
function serverError(detail: string) {
  return { status: 500, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

test('a failed uninstall notifies and leaves the row installed', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await installMockBackend(page)
  await page.route('**/kube-helm-api/helm-delete-chart', (r) =>
    r.fulfill(serverError('Chart uninstall failed: release is locked')),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()
  await confirmAction(page, 'Uninstall extension')

  await expect(page.getByText('Uninstall failed', { exact: true })).toBeVisible()
  await expect(page.getByText('release is locked')).toBeVisible()
  // The extension is still deployed, so the row must keep offering Uninstall.
  await expect(page.getByRole('button', { name: 'Uninstall', exact: true })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a failed marketplace refresh notifies and keeps the list', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await installMockBackend(page)
  await page.route(/\/kube-helm-api\/update-extensions(\?.*)?$/, (r) =>
    r.fulfill(serverError('helm repo update failed')),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByTestId('update-extensions').click()
  await confirmAction(page, 'Download')

  await expect(page.getByText('Refresh failed', { exact: true })).toBeVisible()
  await expect(page.getByText('helm repo update failed')).toBeVisible()
  await expect(page.getByText('MITK Workbench')).toBeVisible()
  expect(pageErrors).toEqual([])
})

// An aborted request leaves the axios error without a `response`.
test('an unreachable import-container notifies instead of throwing', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await installMockBackend(page)
  await page.route(/\/kube-helm-api\/import-container(\?.*)?$/, (r) => r.abort())
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

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
  await installMockBackend(page)
  await page.route('**/aii/projects', (r) => r.fulfill(serverError('project lookup failed')))
  await page.goto(VIEW_PATH)

  // The list is scoped by the document URL, so it still loads.
  await expect(page.getByText('MITK Workbench')).toBeVisible()
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

  await expect(page.getByText('MITK Workbench')).toBeVisible()
  expect(pageErrors).toEqual([])
})
