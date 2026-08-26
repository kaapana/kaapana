import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('renders the typical result tree on load', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)

  const rootReq = page.waitForRequest((r) => {
    const u = new URL(r.url())
    return (
      u.pathname.endsWith('/get-static-website-results-tree') &&
      !u.searchParams.get('prefix') &&
      !u.searchParams.get('continuation_token')
    )
  })
  await page.goto(VIEW_PATH)
  await rootReq

  await expect(page.getByText('nnunet-training-230101')).toBeVisible()
  await expect(page.getByText('total-segmentator-230102')).toBeVisible()
  await expect(page.getByText('overview.html')).toBeVisible()

  // Nothing selected yet, so the right pane shows the placeholder.
  await expect(page.getByRole('heading', { name: 'Workflow results' })).toBeVisible()
})

// Pages are requested in 100-node chunks so a single render burst stays small
// (VTreeview has no virtualization).
test('requests results in bounded pages (limit=100)', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  const limited = page.waitForRequest((r) => {
    const u = new URL(r.url())
    return u.pathname.endsWith('/get-static-website-results-tree') && u.searchParams.get('limit') === '100'
  })
  await page.goto(VIEW_PATH)
  await limited
})

// The real backend sends `children: []` on files too; without normalization
// Vuetify renders an expand toggle (mdi-menu-right/down) on every leaf.
test('folders show an expand toggle but result files do not', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('overview.html')).toBeVisible()

  const folderRow = page.locator('.v-list-item', { hasText: 'nnunet-training-230101' })
  await expect(folderRow.locator('.mdi-menu-right, .mdi-menu-down')).toHaveCount(1)

  const fileRow = page.locator('.v-list-item', { hasText: 'overview.html' })
  await expect(fileRow.locator('.mdi-menu-right, .mdi-menu-down')).toHaveCount(0)
})

test('the search field reads as a search input (magnify icon)', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const searchField = page.locator('.v-input', {
    has: page.getByRole('textbox', { name: 'Search loaded results' }),
  })
  await expect(searchField.locator('.mdi-magnify')).toBeVisible()
})

test('shows no tree rows when the backend returns an empty listing', async ({ page }) => {
  const data = structuredClone(defaultMockData)
  data.root = { items: [], nextContinuationToken: null }
  await seedShellState(page)
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)

  // View mounted (search field present) but the tree has no nodes.
  await expect(page.getByRole('textbox', { name: 'Search loaded results' })).toBeVisible()
  await expect(page.getByText('nnunet-training-230101')).toHaveCount(0)
  await expect(page.locator('.v-treeview .v-list-item')).toHaveCount(0)

  await expect(page.getByRole('heading', { name: 'Workflow results' })).toBeVisible()
})
