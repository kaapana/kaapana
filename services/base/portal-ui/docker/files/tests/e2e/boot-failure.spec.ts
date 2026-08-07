import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
})

test('menu endpoint 500: shell still boots, no menu entries, no iframe', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/portal-api/menu', (r) =>
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
  await page.route('**/portal-api/menu', (r) =>
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
  const stored = await page.evaluate(() => localStorage['project'] ?? null)
  expect(stored).toBeNull()
  const cookie = (await page.context().cookies()).find((c) => c.name === 'Project')
  expect(cookie).toBeUndefined()
})

test('userinfo failure: unauthenticated, menu is not rendered', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/oauth2/userinfo', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  await page.route('**/jsons/testingAuthenticationToken.json', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeHidden()
  await expect(page.locator('iframe.kaapana-iframe')).toHaveCount(0)
})
