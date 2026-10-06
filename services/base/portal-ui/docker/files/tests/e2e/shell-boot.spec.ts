import { test, expect } from '@playwright/test'
import { installMockBackend, stubView } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await stubView(page, '/data-upload-ui')
})

test('boots into the default view with the menu rendered', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()
  await expect(page.getByText('Workflows')).toBeVisible()
  await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', /\/data-gallery-ui$/)
})

test('menu navigation routes to the entry and swaps the iframe', async ({ page }) => {
  await page.goto('/')
  await page.getByText('Workflows', { exact: true }).click()
  await page.getByText('Data Upload').click()
  await expect(page).toHaveURL(/\/workflows\/data-upload/)
  await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', /\/data-upload-ui$/)
})

// The shell inside its own iframe replaces #app before Vuetify exists, so the
// notice colors come from localStorage["settings"] rather than a theme token.
// The expected values are the shared theme's `background` per mode. The
// browser prefers light, so the "system" seed must ask it, not trust the flag.
for (const [mode, seed, background] of [
  ['dark', { themeMode: 'dark', darkMode: true }, 'rgb(18, 18, 18)'],
  ['light', { themeMode: 'light', darkMode: false }, 'rgb(238, 238, 238)'],
  ['system', { themeMode: 'system', darkMode: true }, 'rgb(238, 238, 238)'],
] as const) {
  test(`nested shell shows the notice on the ${mode} background`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' })
    await page.addInitScript((settings) => {
      localStorage['settings'] = JSON.stringify(settings)
    }, seed)
    await page.route('**/nested.html', (r) =>
      r.fulfill({ status: 200, contentType: 'text/html', body: '<iframe src="/"></iframe>' }),
    )
    await page.goto('/nested.html')
    const notice = page.frameLocator('iframe').locator('#app > div')
    await expect(notice).toContainText('This view could not be loaded')
    await expect(notice).toHaveCSS('background-color', background)
  })
}

test('selected project is seeded from the aii project list', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()
  const project = await page.evaluate(() => JSON.parse(localStorage['project'] ?? 'null'))
  expect(project?.name).toBe('admin')
  // No legacy Project cookie is written anymore.
  const cookies = await page.context().cookies()
  expect(cookies.find((c) => c.name === 'Project')).toBeUndefined()
})
