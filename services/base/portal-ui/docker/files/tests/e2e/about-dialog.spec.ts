import { test, expect } from '@playwright/test'
import { installMockBackend, stubView } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await page.route('**/jsons/commonData.json', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        version: 'kaapana-admin-chart:0.7.0 | Build-Timestamp: 2026-01-01 | Build-Branch: main',
      }),
    }),
  )
})

test('opens the about dialog with the medical-device disclaimer and links', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'About Platform' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Kaapana is not a medical device', { exact: false })).toBeVisible()
  await expect(dialog.getByRole('link', { name: /Website/ })).toHaveAttribute(
    'href',
    'https://kaapana.ai',
  )
  await expect(dialog.getByRole('link', { name: /Join Slack/ })).toBeVisible()
  await expect(dialog.getByRole('link', { name: /Report Issue/ })).toBeVisible()
})

test('says so when commonData.json cannot be loaded, keeps the static rows, and retries', async ({
  page,
}) => {
  let failing = true
  await page.route('**/jsons/commonData.json', (r) =>
    failing
      ? r.fulfill({ status: 404, contentType: 'text/html', body: '<html>missing</html>' })
      : r.fallback(),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'About Platform' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('The version information could not be loaded.')).toBeVisible()
  await expect(dialog.getByRole('link', { name: /codebase\.helmholtz\.cloud/ })).toBeVisible()

  failing = false
  await dialog.getByRole('button', { name: 'Try again' }).click()
  await expect(dialog.getByText('0.7.0')).toBeVisible()
  await expect(dialog.getByText('The version information could not be loaded.')).toHaveCount(0)
})

test('renders version rows parsed from commonData.json', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'About Platform' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('0.7.0')).toBeVisible()
  await expect(dialog.getByText('main')).toBeVisible()
  // The repository URL row is always present.
  await expect(dialog.getByRole('link', { name: /codebase\.helmholtz\.cloud/ })).toBeVisible()
})
