import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, VIEW_PATH } from './fixtures/mock-backend'

// The typeface travels with the shared Vuetify configuration. A view that builds
// its own Vuetify instance, or reintroduces a font family of its own, renders in
// whatever the client system substitutes instead, which no assertion about
// layout or behaviour would catch.
test('the view renders in the platform typeface', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()

  const robotoFaces = await page.evaluate(() => {
    const families: string[] = []
    document.fonts.forEach((face) => {
      if (/roboto/i.test(face.family)) families.push(face.family)
    })
    return families
  })
  expect(robotoFaces.length).toBeGreaterThan(0)

  const bodyFont = await page
    .getByRole('heading', { name: 'Workflow results' })
    .evaluate((el) => getComputedStyle(el).fontFamily)
  expect(bodyFont).toMatch(/roboto/i)
})

// The shell owns the theme; the view follows it through the settings it writes.
test('the view follows the shell into the dark theme', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: true }))
  })
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()

  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)

  // The theme has to reach the text as well, not just the application element.
  // A hardcoded colour in the view would leave dark text on the dark surface.
  const channels = await page
    .getByRole('heading', { name: 'Workflow results' })
    .evaluate((el) => getComputedStyle(el).color.match(/\d+/g)!.slice(0, 3).map(Number))
  for (const channel of channels) expect(channel).toBeGreaterThan(200)
})
