import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

// Dev mode surfaces the API docs of the services behind a menu entry
// (kaapana.ai/ui.dev-links). Off by default; the switch lives in SettingsDialog.
const devModeOn = { ...defaultMockData, settings: [{ key: 'devMode', value: true }] }

test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
  await stubView(page, '/data-upload-ui')
})

test('no dev buttons while dev mode is off', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()
  await expect(page.getByRole('button', { name: 'API docs' })).toHaveCount(0)

  await page.getByText('Workflows', { exact: true }).click()
  await expect(page.getByText('Data Upload')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Kaapana Backend' })).toHaveCount(0)
})

test('a single dev link opens directly in a new tab', async ({ page }) => {
  await installMockBackend(page, devModeOn)
  await page.goto('/')
  await page.getByText('Workflows', { exact: true }).click()

  const item = page.locator('nav .v-list-item').filter({ hasText: 'Data Upload' })
  const link = item.getByRole('link', { name: 'Kaapana Backend' })
  await expect(link).toHaveAttribute('href', '/kaapana-backend/docs')
  await expect(link).toHaveAttribute('target', '_blank')
  await expect(link).toHaveAttribute('rel', 'noopener')

  // The button sits inside the entry's own link; clicking it must not route the shell.
  const before = page.url()
  await link.click()
  await expect(page).toHaveURL(before)
})

test('several dev links open a menu, each item targeting a new tab', async ({ page }) => {
  await installMockBackend(page, devModeOn)
  await page.goto('/')

  const item = page.locator('nav .v-list-item').filter({ hasText: 'Datasets' })
  const activator = item.getByRole('button', { name: 'API docs' })
  await expect(activator).toBeVisible()
  // After the shell settled on the project-scoped URL, so the click can be
  // shown not to move it.
  const before = page.url()
  await activator.click()

  // Vuetify's menu overlay carries no menu role, so scope by its content class.
  const menu = page.locator('.v-overlay__content')
  for (const [label, path] of [
    ['Kaapana Backend', '/kaapana-backend/docs'],
    ['AII', '/aii/docs'],
    ['DICOM Web Filter', '/dicom-web-filter/docs'],
  ]) {
    const entry = menu.getByRole('link', { name: label })
    await expect(entry).toHaveAttribute('href', path!)
    await expect(entry).toHaveAttribute('target', '_blank')
    await expect(entry).toHaveAttribute('rel', 'noopener')
  }
  await expect(page).toHaveURL(before)
})

test('clicking a dev link in the menu opens that tab and leaves the shell put', async ({
  page,
}) => {
  await installMockBackend(page, devModeOn)
  await page.goto('/')

  const item = page.locator('nav .v-list-item').filter({ hasText: 'Datasets' })
  await item.getByRole('button', { name: 'API docs' }).click()

  const before = page.url()
  const popupPromise = page.waitForEvent('popup')
  await page.locator('.v-overlay__content').getByRole('link', { name: 'AII' }).click()
  const popup = await popupPromise

  // Only the path is asserted: nothing serves /aii/docs here, so the popup may
  // still be settling on about:blank when the event fires.
  await expect.poll(() => new URL(popup.url(), before).pathname).toBe('/aii/docs')
  await expect(page).toHaveURL(before)
})

test('dev links the roles cannot reach are dropped, entry and all', async ({ page }) => {
  await installMockBackend(page, {
    ...devModeOn,
    policyData: {
      endpoints_per_role: {
        // Both views are reachable, but of their dev links only /aii/docs is.
        user: [
          { path: '^/data-gallery-ui', methods: ['GET'] },
          { path: '^/extensions-ui', methods: ['GET'] },
          { path: '^/aii/docs', methods: ['GET'] },
        ],
      },
    },
    userinfo: {
      preferredUsername: 'kaapana',
      groups: ['role:user'],
      user: '00000000-0000-0000-0000-000000000001',
    },
  })
  await page.goto('/')

  // Datasets keeps one of three links -> direct button, no menu.
  const datasets = page.locator('nav .v-list-item').filter({ hasText: 'Datasets' })
  await expect(datasets.getByRole('link', { name: 'AII' })).toHaveAttribute('href', '/aii/docs')
  await expect(datasets.getByRole('button', { name: 'API docs' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Kaapana Backend' })).toHaveCount(0)

  // Extensions keeps none -> no button at all.
  const extensions = page.locator('nav .v-list-item').filter({ hasText: 'Extensions' })
  await expect(extensions).toBeVisible()
  await expect(extensions.getByRole('button', { name: 'API docs' })).toHaveCount(0)
})

test('the Dev Mode switch applies live and survives Save', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()

  const itemReq = page.waitForRequest(
    (r) => r.url().includes('/kaapana-backend/settings/item') && r.method() === 'PUT',
  )
  await page.getByLabel('Dev Mode').click()
  expect((await itemReq).postDataJSON()).toEqual({ key: 'devMode', value: true })

  const saveReq = page.waitForRequest(
    (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  const body = (await saveReq).postDataJSON()
  expect(body).toContainEqual({ key: 'devMode', value: true })

  // Dialog closed: the drawer now offers the dev buttons.
  await expect(
    page.locator('nav .v-list-item').filter({ hasText: 'Datasets' }).getByRole('button', {
      name: 'API docs',
    }),
  ).toBeVisible()
})
