import { test, expect, type Page } from '@playwright/test'
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

  test('titles use the platform type scale', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1, name: 'Data upload' })).toHaveClass(
      /text-h4/,
    )
    const sections = page.getByRole('heading', { level: 2 })
    await expect(sections).toHaveCount(2)
    for (const section of await sections.all()) {
      await expect(section).toHaveClass(/text-h5/)
    }
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

test.describe('layout', () => {
  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1200 })
    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1200)
    // Centred: equal margins on both sides.
    expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
  })

  test('a narrow window does not scroll sideways', async ({ page }) => {
    await page.setViewportSize({ width: 420, height: 900 })
    const widths = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }))
    expect(widths.scroll).toBeLessThanOrEqual(widths.client)
  })

  test('the upload steps are an ordered list', async ({ page }) => {
    const steps = page.locator('ol.upload-steps > li')
    await expect(steps).toHaveCount(3)
    await expect(steps.nth(1).locator('.filepond--root')).toBeVisible()
    await expect(steps.nth(2).getByRole('button', { name: /Import the data/ })).toBeVisible()
  })
})

test.describe('dialogs', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
  })

  // The dialog role sits on the full-screen overlay; the card is its content.
  const dialogContent = (page: Page) => page.locator('.v-overlay--active .v-overlay__content')

  test('the info dialog has the medium width and returns focus to its button', async ({ page }) => {
    // An icon-only control needs an accessible name.
    const infoButton = page.getByRole('button', { name: 'How should the uploaded data look?' })
    await infoButton.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    // Poll: the dialog scales in, so its box grows during the transition.
    await expect.poll(async () => (await dialogContent(page).boundingBox())?.width).toBe(600)

    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(infoButton).toBeFocused()
  })

  test('the import dialog has the medium width and returns focus to its button', async ({
    page,
  }) => {
    const importButton = page.getByRole('button', { name: /Import the data/ })
    await importButton.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
    // Poll: the dialog scales in, so its box grows during the transition.
    await expect.poll(async () => (await dialogContent(page).boundingBox())?.width).toBe(600)

    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(importButton).toBeFocused()
  })
})
