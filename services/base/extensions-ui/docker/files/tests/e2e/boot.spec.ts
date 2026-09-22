import { test, expect } from '@playwright/test'
import { defaultMockData } from './fixtures/mock-backend'
import { collectPageErrors, openView } from './fixtures/helpers'

// Regression class that cost data-gallery-ui a blank page: installMockBackend
// seeds localStorage["settings"] for every other spec, so only this one sees a
// fresh-profile boot — an unguarded JSON.parse in App.vue's setup would blank
// the whole document.
test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  const consoleErrors: string[] = []
  page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()))

  await openView(page, defaultMockData, { seedSettings: false })

  expect(pageErrors).toEqual([])
  // Vue routes a throw from setup() to console.error, not window.onerror, so
  // pageerror alone cannot see this. Match the error NAME — the message wording
  // is engine-version specific.
  expect(consoleErrors.filter((t) => /SyntaxError/.test(t))).toEqual([])
})

test('follows the shell dark-mode setting', async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem('settings', JSON.stringify({ darkMode: true })),
  )
  await openView(page, defaultMockData, { seedSettings: false })

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})
