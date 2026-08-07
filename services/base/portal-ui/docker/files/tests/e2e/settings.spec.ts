import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
})

test('seeds localStorage["settings"] (defaults) before the view mounts', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  expect(settings.darkMode).toBe(true)
  expect(settings.datasets.cols).toBe('auto')
})

test('DB settings are merged over the defaults', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    settings: [{ key: 'darkMode', value: false }],
  })
  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  expect(settings.darkMode).toBe(false)
  // The merge keeps default keys the DB did not override.
  expect(settings.datasets.cols).toBe('auto')
  // darkMode:false -> light theme applied on boot.
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('boots into the dark theme by default', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
})

test('the dark-mode switch flips the theme and PUTs the single item', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()

  const itemReq = page.waitForRequest(
    (r) => r.url().includes('/kaapana-backend/settings/item') && r.method() === 'PUT',
  )
  await page.getByLabel('Dark Mode').click()
  const req = await itemReq
  expect(req.postDataJSON()).toEqual({ key: 'darkMode', value: false })
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('Save persists the whole settings object as an array', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()

  const saveReq = page.waitForRequest(
    (r) =>
      /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  const req = await saveReq
  const body = req.postDataJSON()
  expect(Array.isArray(body)).toBe(true)
  expect(body.map((i: { key: string }) => i.key)).toContain('datasets')
})

test('Restore default configuration persists the defaults', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()

  const saveReq = page.waitForRequest(
    (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Restore default configuration' }).click()
  const body = (await saveReq).postDataJSON()
  expect(Array.isArray(body)).toBe(true)
})

test('a failing settings load keeps the last good seed and toasts', async ({ page }) => {
  const pageErrors: string[] = []
  // The fixture's swallowed WebSocket route reports a close on teardown; that is
  // the mock, not the app.
  page.on('pageerror', (err) => {
    if (!/WebSocket closed without opened/.test(err.message)) pageErrors.push(err.message)
  })
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'settings backend down' }),
        })
      : r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  // A previous successful boot left a seed the embedded views already read.
  const lastGood = JSON.stringify({ darkMode: false, datasets: { cols: '3' } })
  await page.addInitScript((seed) => localStorage.setItem('settings', seed), lastGood)
  await page.goto('/')

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not load your settings'),
  ).toBeVisible()
  expect(await page.evaluate(() => localStorage['settings'])).toBe(lastGood)
  expect(pageErrors).toEqual([])
})

test('a failing settings load with no seed still seeds the defaults', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  expect(settings.datasets.cols).toBe('auto')
})

test('the dark-mode switch toasts when the PUT fails, keeping the flip', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings/item', (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'no write access' }),
    }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByLabel('Dark Mode').click()

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not save dark mode'),
  ).toBeVisible()
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('Save toasts when the PUT fails and still closes the dialog', async ({ page }) => {
  const pageErrors: string[] = []
  // The fixture's swallowed WebSocket route reports a close on teardown; that is
  // the mock, not the app.
  page.on('pageerror', (err) => {
    if (!/WebSocket closed without opened/.test(err.message)) pageErrors.push(err.message)
  })
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      : r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'no write access' }),
        }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not save settings'),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeHidden()
  expect(pageErrors).toEqual([])
})
