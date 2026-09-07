import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await stubView(page, '/data-upload-ui')
})

test('renders top-level entries and section headers, entries hidden until expanded', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()
  await expect(page.getByText('Extensions')).toBeVisible()
  await expect(page.getByText('Workflows', { exact: true })).toBeVisible()
  await expect(page.getByText('System', { exact: true })).toBeVisible()
  // Sections start collapsed.
  await expect(page.getByText('Data Upload')).toBeHidden()
})

test('expanding a section reveals its entries', async ({ page }) => {
  await page.goto('/')
  await page.getByText('Workflows', { exact: true }).click()
  await expect(page.getByText('Data Upload')).toBeVisible()
  await expect(page.getByText('Workflow Execution')).toBeVisible()
})

test('open-strategy single: opening a section closes the previously open one', async ({ page }) => {
  await page.goto('/')
  await page.getByText('Workflows', { exact: true }).click()
  await expect(page.getByText('Data Upload')).toBeVisible()
  await page.getByText('System', { exact: true }).click()
  await expect(page.getByText('Data Upload')).toBeHidden()
  await expect(page.getByText('Monitoring')).toBeVisible()
})

test('tab-target entry renders as an external link, not an in-shell route', async ({ page }) => {
  await page.goto('/')
  await page.getByText('System', { exact: true }).click()
  const monitoring = page.getByRole('link', { name: 'Monitoring' })
  await expect(monitoring).toHaveAttribute('href', '/grafana/')
  await expect(monitoring).toHaveAttribute('target', '_blank')
})

test('collapse to rail hides the brand text and project selector, expand restores them', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page.getByText('Kaapana')).toBeVisible()
  await expect(page.getByLabel('Project')).toBeVisible()

  await page.getByRole('button', { name: 'Collapse Sidebar' }).click()
  await expect(page.getByText('Kaapana')).toBeHidden()
  await expect(page.getByLabel('Project')).toBeHidden()

  await page.getByRole('button', { name: 'Expand Sidebar' }).click()
  await expect(page.getByText('Kaapana')).toBeVisible()
  await expect(page.getByLabel('Project')).toBeVisible()
})

test('brand shows the admin-chart version parsed from commonData.json', async ({ page }) => {
  await page.route('**/jsons/commonData.json', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ version: 'kaapana-admin-chart:0.7.0-latest | Build-Timestamp: x' }),
    }),
  )
  await page.goto('/')
  await expect(page.getByText('0.7.0-latest')).toBeVisible()
})

// The error state itself is covered in boot-failure.spec.ts: it can only render
// when no entry does, so asserting its absence here would be vacuous.
test('a failing poll keeps the last known menu', async ({ page }) => {
  await page.clock.install()
  let failing = false
  let failedPolls = 0
  await page.route('**/portal-api/menu', (r) => {
    if (failing) {
      failedPolls++
      return r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
    }
    return r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(defaultMockData.menu),
    })
  })
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()

  failing = true
  await page.clock.runFor(15_000)
  // The surviving menu only means anything once a poll has actually failed.
  await expect.poll(() => failedPolls).toBeGreaterThan(0)

  await expect(page.getByText('Datasets')).toBeVisible()
})

test('OPA filtering hides entries the user is not authorized for', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    policyData: {
      endpoints_per_role: {
        // The user's only role authorizes just the gallery view.
        user: [{ path: '^/data-gallery-ui', methods: ['GET'] }],
      },
    },
    userinfo: {
      preferredUsername: 'kaapana',
      groups: ['role:user'],
      user: '00000000-0000-0000-0000-000000000001',
    },
  })
  await page.goto('/')
  await expect(page.getByText('Datasets')).toBeVisible()
  // Whole "Workflows" section is empty (no visible entries) and "Extensions"
  // is unauthorized -> neither appears.
  await expect(page.getByText('Workflows', { exact: true })).toBeHidden()
  await expect(page.getByText('Extensions')).toBeHidden()
})
