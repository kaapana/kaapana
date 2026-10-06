import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

// The typeface and the theme come from the shared Vuetify configuration. If the
// shell built its own Vuetify instance again, no behaviour test would notice.
test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
})

test('the shell renders in the platform typeface', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()

  const robotoFaces = await page.evaluate(() => {
    const families: string[] = []
    document.fonts.forEach((face) => {
      if (/roboto/i.test(face.family)) families.push(face.family)
    })
    return families
  })
  expect(robotoFaces.length).toBeGreaterThan(0)

  const drawerFont = await page
    .getByText('Datasets')
    .evaluate((el) => getComputedStyle(el).fontFamily)
  expect(drawerFont).toMatch(/roboto/i)
})

// The brand sits inside a link. Without a fix it takes the theme's link colour,
// which is hard to read on the blue header.
for (const mode of ['dark', 'light'] as const) {
  test(`the brand header keeps its white text in ${mode} mode`, async ({ page }) => {
    await installMockBackend(page, {
      ...defaultMockData,
      settings: [{ key: 'themeMode', value: mode }],
    })
    await page.route('**/jsons/commonData.json', (r) =>
      r.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ version: 'kaapana-admin-chart:0.7.0-256-g4ae14bb9c6 | Build: x' }),
      }),
    )
    await page.goto('/')
    const name = page.locator('nav').getByText('Kaapana', { exact: true })
    await expect(name).toHaveCSS('color', 'rgb(255, 255, 255)')
    const version = page.getByText('0.7.0-256-g4ae14bb9c6')
    await expect(version).toHaveCSS('color', 'rgb(255, 255, 255)')
    // A long development version is cut, not wrapped onto a second line.
    const box = await version.boundingBox()
    expect(box!.height).toBeLessThan(24)
  })
}

test('the light theme paints the shared page background, not plain white', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    settings: [{ key: 'darkMode', value: false }],
  })
  await page.goto('/')
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
  await expect(page.locator('.v-application')).toHaveCSS('background-color', 'rgb(238, 238, 238)')
})
