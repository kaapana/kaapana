import { test, expect } from '@playwright/test'
import { lastDirty, openGallery, trackDirty } from './fixtures/helpers'

// The view posts kaapana:view-dirty to its parent, so the shell can ask before
// leaving or reloading the view. Standalone, the window is its own parent
// (window.parent === window), so the messages land here, where trackDirty
// captures them.

test('adding a filter reports the view dirty; removing it reports clean', async ({ page }) => {
  await trackDirty(page)
  await openGallery(page)

  // Clean on boot: an empty search posts nothing.
  expect(await lastDirty(page)).toBeNull()

  await page.locator('button:has(.mdi-filter-plus-outline)').click()
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.locator('button:has(.mdi-delete)').first().click()
  await expect.poll(() => lastDirty(page)).toBe(false)
})

// A shell settings change beyond dark mode remounts the view (App.vue keys the
// router view on useShellSettings' viewKey), which drops the unsaved search; the
// view must then report itself clean, or the shell keeps warning about work that
// is gone.
test('a view remounted by a shell settings change reports itself clean', async ({ page }) => {
  await trackDirty(page)
  await openGallery(page)
  await page.getByLabel('Search').first().fill('Thorax')
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.evaluate(() => {
    const oldValue = localStorage.getItem('settings')
    const settings = JSON.parse(oldValue ?? '{}')
    settings.datasets.cols = 4
    const newValue = JSON.stringify(settings)
    localStorage.setItem('settings', newValue)
    window.dispatchEvent(new StorageEvent('storage', { key: 'settings', oldValue, newValue }))
  })

  await expect(page.getByLabel('Search').first()).toHaveValue('')
  await expect.poll(() => lastDirty(page)).toBe(false)
})

test('a free-text query reports the view dirty; clearing it reports clean', async ({ page }) => {
  await trackDirty(page)
  await openGallery(page)

  await page.getByLabel('Search').first().fill('Thorax')
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.getByLabel('Search').first().fill('')
  await expect.poll(() => lastDirty(page)).toBe(false)
})
