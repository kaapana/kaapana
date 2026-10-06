import { test, expect } from '@playwright/test'
import { MENU_ROUTE, installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
})

test('menu endpoint 500: shell still boots, no menu entries, no iframe', async ({ page }) => {
  await installMockBackend(page)
  await page.route(MENU_ROUTE, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/')
  // Brand chrome renders even with an empty menu.
  await expect(page.getByText('Kaapana')).toBeVisible()
  await expect(page.getByText('Datasets')).toBeHidden()
  await expect(page.locator('iframe.kaapana-iframe')).toHaveCount(0)
  // Drawer and main area both name the reason instead of staying blank.
  await expect(page.getByText('Menu unavailable')).toBeVisible()
  await expect(page.getByText('No view available')).toBeVisible()
})

// Regression: with idleLogout.start() inside onMounted's try, a menu 500
// skipped it and the session never timed out. The 1800000ms countdown is
// driven with the fake clock.
const IDLE_TIMEOUT_MS = 1_800_000

test('a failed boot still arms the idle logout timer', async ({ page }) => {
  await page.clock.install()
  await installMockBackend(page)
  await page.route(MENU_ROUTE, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  // The logout target is a real top-window navigation; stub it so the assertion
  // is about the navigation and not about what the dev server serves for it.
  await page.route('**/kaapana-backend/oidc-logout', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>bye</body></html>' }),
  )
  await page.goto('/')

  // The boot really did fail.
  await expect(page.getByText('Menu unavailable')).toBeVisible()

  await page.clock.runFor(IDLE_TIMEOUT_MS + 1_000)
  await page.waitForURL('**/kaapana-backend/oidc-logout')
})

test('empty menu: drawer and main area explain there is nothing to show', async ({ page }) => {
  await installMockBackend(page, { ...defaultMockData, menu: { items: [] } })
  await page.goto('/')
  await expect(page.getByText('No entries')).toBeVisible()
  await expect(page.getByText('Menu unavailable')).toBeHidden()
  await expect(page.getByText('No view available')).toBeVisible()
  await expect(page.locator('iframe.kaapana-iframe')).toHaveCount(0)
})

test('OPA hides every entry: drawer shows the empty message, not the error one', async ({
  page,
}) => {
  await installMockBackend(page, {
    ...defaultMockData,
    policyData: { endpoints_per_role: { user: [{ path: '^/nothing', methods: ['GET'] }] } },
    userinfo: {
      preferredUsername: 'kaapana',
      groups: ['role:user'],
      user: '00000000-0000-0000-0000-000000000001',
    },
  })
  await page.goto('/')
  await expect(page.getByText('No entries')).toBeVisible()
  await expect(page.getByText('Menu unavailable')).toBeHidden()
})

test('empty project list: no project selected, no cookie/localStorage seeded', async ({ page }) => {
  await installMockBackend(page, { ...defaultMockData, projects: [] })
  await page.goto('/')
  // Menu still loads, so the default view is shown.
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  // An empty list is a fact about the user, not a failure.
  await expect(page.getByText('You are not a member of any project.')).toBeVisible()
  await expect(page.getByText('Could not load projects.')).toHaveCount(0)
  const stored = await page.evaluate(() => localStorage['project'] ?? null)
  expect(stored).toBeNull()
  const cookie = (await page.context().cookies()).find((c) => c.name === 'Project')
  expect(cookie).toBeUndefined()
})

test('project list 500: the selector names the failure and Try again recovers', async ({
  page,
}) => {
  await installMockBackend(page)
  let failing = true
  await page.route('**/aii/projects', (r) =>
    failing
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(defaultMockData.projects),
        }),
  )
  await page.goto('/')
  await expect(page.getByText('Could not load projects.')).toBeVisible()
  await expect(page.getByText('You are not a member of any project.')).toHaveCount(0)

  failing = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByLabel('Project')).toBeVisible()
  // The recovered selection scopes the URL like a normal boot does.
  await expect(page).toHaveURL(/\/project\/admin/)
})

test('menu endpoint 500: Try again fetches the menu in place', async ({ page }) => {
  await installMockBackend(page)
  let failing = true
  await page.route(MENU_ROUTE, (r) =>
    failing
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(defaultMockData.menu),
        }),
  )
  await page.goto('/')
  await expect(page.getByText('Menu unavailable')).toBeVisible()

  failing = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('Datasets')).toBeVisible()
  await expect(page.getByText('Menu unavailable')).toHaveCount(0)
  await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
    'src',
    '/project/admin/data-gallery-ui',
  )
})

test('menu endpoint 500: the URL still carries the project, and so do backend calls', async ({
  page,
}) => {
  await installMockBackend(page)
  await page.route(MENU_ROUTE, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  const settingsRead = page.waitForRequest(
    (r) => r.url().includes('/kaapana-backend/settings') && r.method() === 'GET',
  )
  await page.goto('/')
  await expect(page.getByText('Menu unavailable')).toBeVisible()
  await expect(page).toHaveURL(/\/project\/admin\/?$/)
  expect(new URL((await settingsRead).url()).pathname).toBe(
    '/project/admin/kaapana-backend/settings',
  )
})

test('menu endpoint 500 on a deep link: Try again opens that view, not the default', async ({
  page,
}) => {
  await installMockBackend(page)
  await stubView(page, '/data-upload-ui')
  let failing = true
  await page.route(MENU_ROUTE, (r) =>
    failing
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(defaultMockData.menu),
        }),
  )
  await page.goto('/project/admin/workflows/data-upload')
  await expect(page.getByText('Menu unavailable')).toBeVisible()
  await expect(page).toHaveURL(/\/project\/admin\/workflows\/data-upload$/)

  failing = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
    'src',
    '/project/admin/data-upload-ui',
  )
})

test('userinfo failure: the shell says it could not start, and Try again recovers', async ({
  page,
}) => {
  await installMockBackend(page)
  const settingsReads: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('/kaapana-backend/settings') && r.method() === 'GET') {
      settingsReads.push(new URL(r.url()).pathname)
    }
  })
  // Prod asks the oauth2 proxy, the dev server a static token file.
  let failing = true
  const userinfo = (r: import('@playwright/test').Route) =>
    failing
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(defaultMockData.userinfo),
        })
  await page.route('**/oauth2/userinfo', userinfo)
  await page.route('**/jsons/testingAuthenticationToken.json', userinfo)
  await page.goto('/')
  // Not a blank page: the failure is named, and nothing else is rendered.
  await expect(page.getByText('The platform could not start')).toBeVisible()
  await expect(page.getByText('Datasets')).toBeHidden()
  await expect(page.locator('iframe.kaapana-iframe')).toHaveCount(0)

  // The technical detail is one click away.
  await page.getByRole('button', { name: 'Details' }).click()
  const details = page.getByRole('dialog').filter({ hasText: 'Copy details' })
  await expect(details.getByText('500 Internal Server Error')).toBeVisible()
  await details.getByRole('button', { name: 'Close' }).click()

  failing = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('Datasets')).toBeVisible()
  await expect(page.getByText('The platform could not start')).toHaveCount(0)
  // The recovered shell is scoped like a normal boot, before it reads the settings.
  await expect(page).toHaveURL(/\/project\/admin\/?$/)
  expect(settingsReads).toEqual(['/project/admin/kaapana-backend/settings'])
})

test('a slow boot shows progress instead of a blank page', async ({ page }) => {
  await installMockBackend(page)
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  const userinfo = async (r: import('@playwright/test').Route) => {
    await gate
    await r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(defaultMockData.userinfo),
    })
  }
  await page.route('**/oauth2/userinfo', userinfo)
  await page.route('**/jsons/testingAuthenticationToken.json', userinfo)
  // The first navigation waits on the router, which waits on userinfo.
  const navigation = page.goto('/')
  await expect(page.getByLabel('Loading the platform')).toBeVisible()

  release()
  await navigation
  await expect(page.getByText('Datasets')).toBeVisible()
  await expect(page.getByLabel('Loading the platform')).toHaveCount(0)
})
