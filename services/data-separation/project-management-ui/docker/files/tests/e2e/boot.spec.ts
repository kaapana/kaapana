import { test, expect } from '@playwright/test'
import { ADMIN_PROJECT, defaultMockData, RESEARCH_PROJECT } from './fixtures/mock-backend'
import { collectPageErrors, openProject, openView, row } from './fixtures/helpers'

test('renders the project list on a fresh profile', async ({ page }) => {
  const pageErrors = collectPageErrors(page)

  await openView(page, defaultMockData, { seedSettings: false })

  await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('opens a project from the list', async ({ page }) => {
  await openView(page)

  await row(page, RESEARCH_PROJECT.name).getByRole('button', { name: 'View' }).click()

  await expect(page).toHaveURL(new RegExp(`/projects-ui/project/${RESEARCH_PROJECT.id}$`))
  await expect(page.getByText(RESEARCH_PROJECT.description!)).toBeVisible()
})

test('renders a project detail page directly', async ({ page }) => {
  const pageErrors = collectPageErrors(page)

  await openProject(page, ADMIN_PROJECT)

  await expect(page.getByText('Project Users')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('follows the shell dark-mode setting', async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem('settings', JSON.stringify({ darkMode: true })),
  )
  await openView(page, defaultMockData, { seedSettings: false })

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})

test('switches theme live when the shell toggles dark mode', async ({ page }) => {
  await openView(page)
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)

  // The shell writes in another browsing context; a same-document write fires
  // no storage event, so dispatch the one the shell's write would cause.
  await page.evaluate(() => {
    const oldValue = localStorage.getItem('settings')
    const newValue = JSON.stringify({ darkMode: true })
    localStorage.setItem('settings', newValue)
    window.dispatchEvent(new StorageEvent('storage', { key: 'settings', oldValue, newValue }))
  })

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})
