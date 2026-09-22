import { test, expect } from '@playwright/test'
import { defaultMockData } from './fixtures/mock-backend'
import { catalogue, extension, openView, row } from './fixtures/helpers'

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
  await expect(page.getByText('4 of 5 extensions match the current filters')).toBeVisible()
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

test('an empty catalogue explains itself and offers the first action', async ({ page }) => {
  await openView(page, catalogue([]))

  const empty = page.getByTestId('extensions-empty-state')
  await expect(empty.locator('.v-empty-state')).toContainText('No extensions available yet')
  await expect(empty.getByRole('button', { name: 'Download latest extensions' })).toBeVisible()
  await expect(page.getByText('No data available')).toHaveCount(0)
})

test('filters that exclude everything are reported as a filter result, with a way out', async ({
  page,
}) => {
  await openView(page)
  await page.getByRole('textbox', { name: 'Search' }).fill('no-such-extension-anywhere')

  const empty = page.getByTestId('extensions-empty-state')
  await expect(empty).toContainText('No extensions match the current filters')
  await empty.getByRole('button', { name: 'Reset filters' }).click()
  await expect(row(page, 'MITK Workbench')).toBeVisible()
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
