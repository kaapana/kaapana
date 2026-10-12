import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

// Cross-cutting rules of the Kaapana frontend design guidelines that no single
// feature owns. A failure here is a regression against the design system.

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: 'Data upload' })).toBeVisible()
})

test.describe('visual language', () => {
  test('the platform typeface ships with the view', async ({ page }) => {
    await expect(page.locator('#kaapana-platform-fonts')).toHaveCount(1)
    const robotoFaces = await page.evaluate(
      () => [...document.fonts].filter((face) => face.family.includes('Roboto')).length,
    )
    expect(robotoFaces).toBeGreaterThan(0)
  })

  test('no local font rule overrides the platform typeface', async ({ page }) => {
    const fonts = await page.evaluate(() => ({
      app: getComputedStyle(document.querySelector('#app')!).fontFamily,
      button: getComputedStyle(document.querySelector('.v-btn')!).fontFamily,
    }))
    expect(fonts.app).toContain('Roboto')
    expect(fonts.button).toContain('Roboto')
  })
})
