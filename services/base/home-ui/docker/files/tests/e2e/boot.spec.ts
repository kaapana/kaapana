import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

// Regression class that cost data-gallery-ui a blank page: every other spec
// seeds localStorage["settings"], so only this one sees a fresh-profile boot —
// an unguarded JSON.parse in App.vue's setup would blank the whole document.
test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })

  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  await expect(page.getByText('You are working in project')).toBeVisible()
  expect(pageErrors).toEqual([])
  // Vue routes a throw from setup() to console.error, not window.onerror, so
  // pageerror alone cannot see this. Match the error NAME — the message wording
  // is engine-version specific.
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

// Same fresh profile, so the view has to fall back to the defaults it ships
// with. They cover one setting: the fields the detail dialog groups by.
test('a fresh profile falls back to the local grouping fields', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const detailRequest = page.waitForRequest(
    (r) =>
      r.url().includes('/kaapana-backend/dataset/dashboard') &&
      r.method() === 'POST' &&
      r.postDataJSON().names.length > 0,
  )
  await page.getByRole('button', { name: 'Details' }).click()
  expect((await detailRequest).postDataJSON().names).toEqual(['Patient Sex', 'Modality'])
})
