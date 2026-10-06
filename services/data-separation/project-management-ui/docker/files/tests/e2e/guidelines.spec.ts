import { test, expect } from '@playwright/test'
import { RESEARCH_PROJECT } from './fixtures/mock-backend'
import { openView, row } from './fixtures/helpers'

// Rules from docs/source/development_guide/preview/design_guidelines.rst that
// hold for every control.

test.describe('visual language', () => {
  test('the shared theme is in effect: platform typeface and theme roles', async ({ page }) => {
    await openView(page)

    const fonts = await page.evaluate(() => ({
      app: getComputedStyle(document.querySelector('#app')!).fontFamily,
      body: getComputedStyle(document.body).fontFamily,
    }))
    expect(fonts.app).toContain('Roboto')
    expect(fonts.body).toContain('Roboto')

    const lightThemePrimary = 'rgb(0, 91, 160)'
    const view = row(page, RESEARCH_PROJECT.name).getByRole('button', { name: 'View' })
    await expect(view).toHaveCSS('color', lightThemePrimary)
  })

  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await openView(page)
    await page.setViewportSize({ width: 2560, height: 1200 })

    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1600)
    const leftMargin = box.x
    const rightMargin = 2560 - box.width - box.x
    expect(Math.abs(leftMargin - rightMargin)).toBeLessThan(2)
  })

  test('table actions are tertiary; the page keeps one filled primary action', async ({ page }) => {
    await openView(page)

    const filled = page.locator('.v-btn.bg-primary')
    await expect(filled).toHaveCount(1)
    await expect(filled).toHaveText('Create New Project')

    const research = row(page, RESEARCH_PROJECT.name)
    const view = research.getByRole('button', { name: 'View' })
    await expect(view).toHaveClass(/text-primary/)
    await expect(view).not.toHaveClass(/bg-primary/)
    await expect(research.locator('.v-btn.text-error')).toHaveCount(1)
    await expect(research.locator('.v-btn.bg-error')).toHaveCount(0)
  })
})
