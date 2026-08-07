import { test, expect } from '@playwright/test'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'
import type { ExtensionMock } from './fixtures/mock-backend'

test('renders the extension list with mixed installed states', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByText('MITK Workbench')).toBeVisible()
  await expect(page.getByText('nnU-Net Training')).toBeVisible()
  await expect(page.getByText('Code Server')).toBeVisible()
  await expect(page.getByText('JupyterLab')).toBeVisible()

  // installed -> Uninstall, not-installed single -> Install,
  // not-installed multi -> Launch, in-progress -> Pending.
  await expect(page.getByRole('button', { name: 'Uninstall' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Install', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Launch' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pending' })).toBeVisible()
})

test('hides experimental extensions behind the default maturity filter', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByText('MITK Workbench')).toBeVisible()
  await expect(page.getByText('Experimental Tool')).toHaveCount(0)
})

test('shows a pending extension with an in-progress indicator', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('button', { name: 'Pending' })).toBeVisible()
  // The Ready column renders an indeterminate spinner for pending installs.
  await expect(page.getByRole('progressbar')).toBeVisible()
})

test('shows every extension on one page by default', async ({ page }) => {
  // 30 rows exceed every paginated page size the footer offers, so a truncated
  // table would be obvious here.
  const many: ExtensionMock[] = Array.from({ length: 30 }, (_, i) => ({
    ...defaultMockData.extensions[0]!,
    releaseName: `bulk-${i}`,
    name: `bulk-${i}`,
    chart_name: `bulk-${i}`,
    display_name: `Bulk Extension ${i}`,
    available_versions: { '1.0.0': { deployments: [] } },
    installed: 'no',
    successful: null,
    links: [],
  }))
  await installMockBackend(page, { ...defaultMockData, extensions: many })
  await page.goto(VIEW_PATH)

  await expect(page.locator('tbody tr')).toHaveCount(30)
  // The page-size selector must render "All", not a blank current value.
  await expect(page.locator('.v-data-table-footer__items-per-page')).toContainText('All')
})

test('renders an empty table when no extensions are available', async ({ page }) => {
  await installMockBackend(page, { ...defaultMockData, extensions: [] })
  await page.goto(VIEW_PATH)

  await expect(page.getByText('No data available')).toBeVisible()
})

test('renders a row whose version is absent from available_versions without crashing the table', async ({ page }) => {
  // Realistic drift: the selected version has no matching available_versions
  // entry, so the per-row deployment lookup would index into undefined.
  const brokenExtension: ExtensionMock = {
    releaseName: 'broken-ext',
    name: 'broken-ext',
    chart_name: 'broken-ext',
    version: '9.9.9',
    versions: ['9.9.9'],
    available_versions: { '1.0.0': { deployments: [] } },
    multiinstallable: 'no',
    kind: 'application',
    experimental: 'no',
    resourceRequirement: 'cpu',
    successful: null,
    installed: 'no',
    description: 'Version missing from available_versions',
    display_name: 'Broken Extension',
    keywords: ['kaapana-application'],
  }
  await installMockBackend(page, {
    ...defaultMockData,
    extensions: [brokenExtension, ...defaultMockData.extensions],
  })
  await page.goto(VIEW_PATH)

  // The malformed row renders degraded (treated as not installed -> "Install")
  // instead of throwing and killing the whole table render.
  await expect(page.getByText('Broken Extension')).toBeVisible()
  // Sibling rows are unaffected.
  await expect(page.getByText('MITK Workbench')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Uninstall' })).toBeVisible()
})

test('survives a backend error, shows no rows, and notifies the user', async ({ page }) => {
  // Freeze the 5s poll so exactly one failed load (the initial one) fires and a
  // single toast exists to assert against.
  await page.clock.install()
  await installMockBackend(page)
  // Override the extensions route to fail (later route wins).
  await page.route(/\/kube-helm-api\/extensions(\?.*)?$/, (r) =>
    r.fulfill({ status: 500, contentType: 'text/plain', body: 'internal error' }),
  )
  await page.goto(VIEW_PATH)

  await expect(page.getByLabel('Search')).toBeVisible()
  await expect(page.getByText('No data available')).toBeVisible()
  await expect(page.getByText('MITK Workbench')).toHaveCount(0)

  // Unlike a legitimately empty list, a load failure surfaces an error toast.
  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Failed to load extensions')).toBeVisible()
})
