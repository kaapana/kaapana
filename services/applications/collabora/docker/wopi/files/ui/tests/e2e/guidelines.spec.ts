import { test, expect } from '@playwright/test'
import { openView } from './fixtures/helpers'

test.beforeEach(({ page }) => openView(page))

test('uses the platform typeface', async ({ page }) => {
  const font = await page.evaluate(() => getComputedStyle(document.body).fontFamily)
  expect(font).toContain('Roboto')
})

test('the view stays within a readable width on a wide display', async ({ page }) => {
  await page.setViewportSize({ width: 2560, height: 1200 })

  const box = (await page.locator('.documents').boundingBox())!
  expect(box.width).toBeLessThanOrEqual(1200)
  expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
})

test('the page keeps one filled primary action', async ({ page }) => {
  await expect(page.locator('.v-btn.bg-primary')).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Check for new documents' })).toHaveClass(
    /bg-primary/,
  )
})

test('icons come from the shared icon map', async ({ page }) => {
  await expect(page.locator('.mdi-refresh')).toBeVisible()
  await expect(page.locator('.mdi-magnify')).toBeVisible()
  await expect(page.locator('.mdi-open-in-new')).toHaveCount(3)
})
