import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, VIEW_PATH } from './fixtures/mock-backend'

test.beforeEach(async ({ page, context }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Stub the file url at the context level too, so an open-in-new popup
  // (a fresh Page, not covered by page.route) does not hang.
  await context.route('**/minio-console/**', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>stub</body></html>' }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('overview.html')).toBeVisible()
})

test('selecting a file opens a preview panel with an iframe at its url', async ({ page }) => {
  const fileReq = page.waitForRequest((r) => r.url().includes('/minio-console/download/results/overview.html'))
  await page.locator('.v-list-item', { hasText: 'overview.html' }).getByRole('checkbox').first().check()
  await fileReq

  await expect(page.getByRole('heading', { name: 'Workflow results' })).toBeHidden()
  await expect(page.locator('iframe')).toHaveAttribute('src', /\/minio-console\/download\/results\/overview\.html$/)
})

test('the open-in-new icon opens the file url in a new tab', async ({ page }) => {
  await page.locator('.v-list-item', { hasText: 'overview.html' }).getByRole('checkbox').first().check()
  await expect(page.locator('iframe')).toBeVisible()

  const popupPromise = page.waitForEvent('popup')
  await page.locator('.mdi-open-in-new').first().click()
  const popup = await popupPromise
  expect(popup.url()).toContain('/minio-console/download/results/overview.html')
})

test('selecting multiple files opens a panel per file', async ({ page }) => {
  await page.getByText('nnunet-training-230101').click()
  await expect(page.getByText('report.html')).toBeVisible()

  await page.locator('.v-list-item', { hasText: 'report.html' }).getByRole('checkbox').first().check()
  await page.locator('.v-list-item', { hasText: 'metrics.json' }).getByRole('checkbox').first().check()

  await expect(page.locator('.v-expansion-panel')).toHaveCount(2)
})

// Regression guard for the v-treeview `return-object` binding: without it the
// checkbox still toggles visually but `tree` holds path strings (no .file/.url),
// so selectedFiles stays empty and no panel ever appears.
test('checking a result selects it and the panel reacts; unchecking removes it', async ({ page }) => {
  const checkbox = page.locator('.v-list-item', { hasText: 'overview.html' }).getByRole('checkbox').first()

  await checkbox.check()
  await expect(checkbox).toBeChecked()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(1)
  await expect(page.locator('iframe')).toBeVisible()

  await checkbox.uncheck()
  await expect(checkbox).not.toBeChecked()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Workflow results' })).toBeVisible()
})

// A wrapper with no definite height collapses the iframe to 150 px.
test('the result preview iframe fills the panel instead of collapsing', async ({ page }) => {
  await page.locator('.v-list-item', { hasText: 'overview.html' }).getByRole('checkbox').first().check()

  const iframe = page.locator('iframe').first()
  await expect(iframe).toBeVisible()
  const box = await iframe.boundingBox()
  expect(box!.height).toBeGreaterThan(400)
})
