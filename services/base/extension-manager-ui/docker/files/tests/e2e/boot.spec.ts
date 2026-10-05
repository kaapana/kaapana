import { test, expect } from '@playwright/test'
import { defaultMockData, VIEW_PATH, installMockBackend } from './fixtures/mock-backend'
import { cards, collectPageErrors, openView } from './fixtures/helpers'

test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  const consoleErrors: string[] = []
  page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()))

  await openView(page, 'catalog', defaultMockData(), { seedSettings: false })

  expect(pageErrors).toEqual([])
  expect(consoleErrors.filter((text) => /SyntaxError/.test(text))).toEqual([])
})

test('follows the shell dark-mode setting', async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem('settings', JSON.stringify({ darkMode: true })),
  )
  await openView(page, 'catalog', defaultMockData(), { seedSettings: false })

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})

test('ships no own theme toggle or app bar; the shell owns them', async ({ page }) => {
  await openView(page)

  await expect(page.locator('.v-app-bar')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /dark mode|light mode/i })).toHaveCount(0)
})

test('the root and unknown paths land on the catalog', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page).toHaveURL(/\/extension-manager-ui\/catalog$/)

  await page.goto(`${VIEW_PATH}does-not-exist`)
  await expect(page).toHaveURL(/\/extension-manager-ui\/catalog$/)
})

test('the section tabs switch between catalog, extensions and repositories', async ({ page }) => {
  await openView(page)

  await page.getByRole('tab', { name: 'Extensions' }).click()
  await expect(page).toHaveURL(/\/extensions$/)
  await expect(cards(page).first()).toContainText('totalsegmentator')

  await page.getByRole('tab', { name: 'Repositories' }).click()
  await expect(page).toHaveURL(/\/repositories$/)
  await expect(cards(page).first()).toContainText('kaapana-public')

  await page.getByRole('tab', { name: 'Catalog' }).click()
  await expect(page.getByRole('tab', { name: 'Catalog' })).toHaveAttribute('aria-selected', 'true')
})
