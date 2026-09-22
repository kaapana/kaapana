import { test, expect } from '@playwright/test'
import { defaultMockData, installMockBackend, VIEW_PATH } from './fixtures/mock-backend'
import { catalogue, extension, openView, row, toasts } from './fixtures/helpers'

test('renders the extension list with mixed installed states', async ({ page }) => {
  await openView(page)

  // installed -> Uninstall, not-installed single -> Install,
  // not-installed multi -> Launch, in-progress -> Pending.
  const expected: [string, string][] = [
    ['MITK Workbench', 'Uninstall'],
    ['nnU-Net Training', 'Install'],
    ['JupyterLab', 'Launch'],
    ['Code Server', 'Pending'],
  ]
  for (const [name, action] of expected) {
    await expect(row(page, name).getByRole('button', { name: action, exact: true })).toBeVisible()
  }
})

test('hides experimental extensions behind the default maturity filter', async ({ page }) => {
  await openView(page)

  await expect(row(page, 'Experimental Tool')).toHaveCount(0)
})

test('shows a pending extension with an in-progress indicator', async ({ page }) => {
  await openView(page)

  // The Ready column renders an indeterminate spinner for pending installs.
  await expect(row(page, 'Code Server').getByRole('progressbar')).toBeVisible()
})

test('shows every extension on one page by default', async ({ page }) => {
  // 30 rows exceed every paginated page size the footer offers, so a truncated
  // table would be obvious here.
  const many = Array.from({ length: 30 }, (_, i) =>
    extension({ releaseName: `bulk-${i}`, display_name: `Bulk Extension ${i}` }),
  )
  await openView(page, catalogue(many))

  await expect(page.locator('tbody tr')).toHaveCount(30)
  // The page-size selector must render "All", not a blank current value.
  await expect(page.locator('.v-data-table-footer__items-per-page')).toContainText('All')
})

test('renders an empty table when no extensions are available', async ({ page }) => {
  await openView(page, catalogue([]))

  await expect(page.getByText('No data available')).toBeVisible()
})

test('renders a row whose version is absent from available_versions without crashing the table', async ({
  page,
}) => {
  // Realistic drift: the selected version has no matching available_versions
  // entry, so the per-row deployment lookup would index into undefined.
  const broken = extension({
    releaseName: 'broken-ext',
    display_name: 'Broken Extension',
    version: '9.9.9',
    available_versions: { '1.0.0': { deployments: [] } },
  })
  await openView(page, catalogue([broken, ...defaultMockData.extensions]))

  // The malformed row renders degraded (treated as not installed -> "Install")
  // instead of throwing and killing the whole table render.
  await expect(row(page, 'Broken Extension').getByRole('button', { name: 'Install' })).toBeVisible()
  // Sibling rows are unaffected.
  await expect(row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })).toBeVisible()
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
  await expect(row(page, 'MITK Workbench')).toHaveCount(0)

  // Unlike a legitimately empty list, a load failure surfaces an error toast.
  await expect(toasts(page).getByText('Failed to load extensions')).toBeVisible()
})
