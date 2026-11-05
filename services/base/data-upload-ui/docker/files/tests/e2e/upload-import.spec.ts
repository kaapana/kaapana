import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

// Uploading and importing overlap: a user may start an import as soon as the
// first of several files has arrived. A finished upload must not discard what
// the user typed into an open import form.

const smallFile = { name: 'scan.zip', mimeType: 'application/zip', buffer: Buffer.from('PK mock') }
const SCHEMAS = '**/kaapana-backend/client/get-ui-form-schemas'

test('a finished upload keeps the input of an open import form', async ({ page }) => {
  await installMockBackend(page)
  // Hold the chunk until the form has been edited.
  let releaseChunk: () => void = () => {}
  const chunkHeld = new Promise<void>((resolve) => (releaseChunk = resolve))
  await page.route(/\/kaapana-backend\/client\/file\?patch=/, async (route) => {
    await chunkHeld
    await route.fulfill({ status: 200, contentType: 'text/plain', body: '' })
  })
  let schemaRequests = 0
  page.on('request', (r) => {
    if (r.url().includes('/client/get-ui-form-schemas')) schemaRequests++
  })
  await page.goto(VIEW_PATH)

  await page.locator('input[type="file"]').setInputFiles(smallFile)
  const importButton = page.getByRole('button', { name: /Import the data/ })
  // The import can start while other files are still uploading.
  await expect(importButton).toBeEnabled()
  await importButton.click()

  const workflowName = page.getByLabel('Workflow name')
  await expect(workflowName).toBeVisible()
  await workflowName.fill('my-import')
  const requestsWhileOpen = schemaRequests

  releaseChunk()
  await expect(page.locator('.filepond--file-status-main')).toHaveText('Upload complete')

  await expect(workflowName).toHaveValue('my-import')
  expect(schemaRequests).toBe(requestsWhileOpen)
})

test('reopening the import dialog loads the files uploaded in the meantime', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  const importButton = page.getByRole('button', { name: /Import the data/ })
  const heading = page.getByRole('heading', { name: 'Workflow Execution' })

  await importButton.click()
  await expect(heading).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(heading).toBeHidden()

  await page.locator('input[type="file"]').setInputFiles(smallFile)
  await expect(page.locator('.filepond--file-status-main')).toHaveText('Upload complete')

  const reload = page.waitForRequest(SCHEMAS)
  await importButton.click()
  await reload
  await expect(heading).toBeVisible()
})
