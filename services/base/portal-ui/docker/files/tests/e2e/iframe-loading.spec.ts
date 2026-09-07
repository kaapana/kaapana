import { test, expect } from '@playwright/test'
import { installMockBackend, stubView } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
})

test('loading overlay covers the iframe until its content loads', async ({ page }) => {
  // Gate the data-upload-ui response so the pending state is observable.
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/data-upload-ui**', async (r) => {
    await gate
    await r.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html><body>stub</body></html>',
    })
  })

  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', /\/data-gallery-ui$/)
  await expect(page.locator('.iframe-loading')).toBeHidden()

  await page.getByText('Workflows', { exact: true }).click()
  await page.getByText('Data Upload').click()
  await expect(page.locator('.iframe-loading')).toBeVisible()

  release()
  await expect(page.locator('.iframe-loading')).toBeHidden()
})
