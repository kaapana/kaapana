import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('renders a card per instance with network details', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Instance Overview')).toBeVisible()
  await expect(page.getByText('Instance name: central-node')).toBeVisible()
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  await expect(page.getByText('https://localhost:443')).toBeVisible()
  await expect(page.getByText('https://10.0.0.5:443')).toBeVisible()

  // Local instance exposes the "home" marker + a copy button, no delete;
  // the remote instance exposes a delete button.
  await expect(page.locator('.mdi-home')).toBeVisible()
  await expect(page.locator('button:has(.mdi-trash-can-outline)')).toHaveCount(1)
})

test('shows no instance cards for an empty backend', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [] })
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Instance Overview')).toBeVisible()
  await expect(page.getByText(/Instance name:/)).toHaveCount(0)
})

test('stays functional when the instance list request fails', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.route(/\/client\/get-kaapana-instances/, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' }),
  )
  await page.goto(VIEW_PATH)

  // A failed list load surfaces a user-visible error notification and renders
  // no (stale) cards — the failure is no longer only console-logged.
  await expect(page.getByText('Instance Overview')).toBeVisible()
  await expect(page.getByText('Failed to load instances')).toBeVisible()
  await expect(page.getByText(/Instance name:/)).toHaveCount(0)
})

test('sync remotes triggers the check-for-updates endpoint and refetches', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  const syncReq = page.waitForRequest(
    (r) => /\/client\/check-for-remote-updates/.test(r.url()) && r.method() === 'GET',
  )
  await page.getByRole('button', { name: 'sync remotes' }).click()
  await syncReq
  await expect(page.getByText('Successfully checked for remote updates')).toBeVisible()
})

test('a failed remote sync notifies and skips the instance refetch', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  // Frozen clock: the 15s instance poll must not be mistaken for the refetch.
  await page.clock.install()
  await seedShellState(page)
  await installMockBackend(page)
  await page.route(/\/client\/check-for-remote-updates/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: '{"detail":"remote unreachable"}',
    }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  let refetches = 0
  page.on('request', (r) => {
    if (/\/client\/get-kaapana-instances/.test(r.url())) refetches++
  })

  const synced = page.waitForResponse((r) => /\/client\/check-for-remote-updates/.test(r.url()))
  await page.getByRole('button', { name: 'sync remotes' }).click()
  await synced

  await expect(page.getByText('remote unreachable')).toBeVisible()
  await expect(page.getByText('Successfully checked for remote updates')).toHaveCount(0)
  expect(refetches).toBe(0)
  expect(pageErrors).toEqual([])
})
