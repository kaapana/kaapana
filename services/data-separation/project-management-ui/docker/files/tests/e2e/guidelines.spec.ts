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
})
