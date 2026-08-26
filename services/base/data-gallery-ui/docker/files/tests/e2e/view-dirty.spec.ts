import { test, expect, type Page } from '@playwright/test'
import { bootGallery, makeDefaultMockData } from './fixtures/mock-backend'

// The view posts kaapana:view-dirty to its parent so the shell can warn before a
// project switch reloads the iframe. Standalone (parent === window), so the
// messages land on this window — capture them via an injected listener.
async function trackDirty(page: Page) {
  await page.addInitScript(() => {
    ;(window as unknown as { __dirty: boolean[] }).__dirty = []
    window.addEventListener('message', (e: MessageEvent) => {
      if (e.data?.type === 'kaapana:view-dirty') {
        ;(window as unknown as { __dirty: boolean[] }).__dirty.push(e.data.dirty)
      }
    })
  })
}

function lastDirty(page: Page) {
  return page.evaluate(() => {
    const d = (window as unknown as { __dirty: boolean[] }).__dirty
    return d.length ? d[d.length - 1] : null
  })
}

test('adding a filter reports the view dirty; removing it reports clean', async ({ page }) => {
  await trackDirty(page)
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // Clean on boot: an empty search posts nothing.
  expect(await lastDirty(page)).toBeNull()

  await page.locator('button:has(.mdi-filter-plus-outline)').click()
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.locator('button:has(.mdi-delete)').first().click()
  await expect.poll(() => lastDirty(page)).toBe(false)
})

test('a free-text query reports the view dirty; clearing it reports clean', async ({ page }) => {
  await trackDirty(page)
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.getByLabel('Search').first().fill('Thorax')
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.getByLabel('Search').first().fill('')
  await expect.poll(() => lastDirty(page)).toBe(false)
})
