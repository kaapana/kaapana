import { test, expect } from '@playwright/test'
import { collectPageErrors, openView } from './fixtures/helpers'

test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, { seedSettings: false })

  expect(pageErrors).toEqual([])
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('follows the shell dark-mode setting', async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem('settings', JSON.stringify({ darkMode: true })),
  )
  await openView(page, undefined, { seedSettings: false })

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})

test('switches theme live when the shell changes dark mode', async ({ page }) => {
  await openView(page)

  await page.evaluate(() => {
    const oldValue = localStorage.getItem('settings')
    const newValue = JSON.stringify({ darkMode: true })
    localStorage.setItem('settings', newValue)
    window.dispatchEvent(new StorageEvent('storage', { key: 'settings', oldValue, newValue }))
  })

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})
