import { test, expect } from '@playwright/test'
import { installMockBackend, TASKS_PATH, TASKS_TITLE } from './fixtures/mock-backend'

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
  await page.goto(TASKS_PATH)

  await expect(page.getByRole('heading', { name: TASKS_TITLE })).toBeVisible()
  await expect(page.getByText('Sort by:')).toBeVisible()
  await expect(page.getByText('Segmentation Editor')).toBeVisible()
  expect(pageErrors).toEqual([])
  // Vue routes a throw from setup() to console.error, not window.onerror, so
  // pageerror alone cannot see this. Match the error NAME — the message wording
  // is engine-version specific.
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

test('the view follows the shell into the dark theme', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage['settings'] = JSON.stringify({ darkMode: true })
  })
  await installMockBackend(page)
  await page.goto(TASKS_PATH)
  const heading = page.getByRole('heading', { name: TASKS_TITLE })
  await expect(heading).toBeVisible()

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
  const channels = await heading.evaluate((el) =>
    getComputedStyle(el).color.match(/\d+/g)!.slice(0, 3).map(Number),
  )
  for (const channel of channels) expect(channel).toBeGreaterThan(200)
})
