import { test, expect } from '@playwright/test'
import { documentLinks, openView } from './fixtures/helpers'
import { installMockBackend } from './fixtures/mock-backend'

test('scans MinIO before it lists the documents', async ({ page }) => {
  const calls: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('/documents/')) calls.push(`${r.method()} ${new URL(r.url()).pathname}`)
  })
  await openView(page)

  expect(calls.slice(0, 2)).toEqual(['POST /documents/refresh', 'GET /documents/'])
})

test('lists the most recently modified document first', async ({ page }) => {
  await openView(page)

  await expect(documentLinks(page)).toHaveCount(3)
  await expect(documentLinks(page).first()).toContainText('notes/protocol.odt')
  await expect(documentLinks(page).last()).toContainText('analysis/volumes.xlsx')
})

test('shows the bucket and the modification date of each document', async ({ page }) => {
  await openView(page)

  await expect(documentLinks(page).last()).toContainText('project-lung · Modified')
})

test('sorts by path alphabetically', async ({ page }) => {
  await openView(page)

  await page.locator('.v-select').click()
  await page.getByRole('option', { name: 'Path' }).click()

  await expect(documentLinks(page)).toContainText([
    'analysis/volumes.xlsx',
    'notes/protocol.odt',
    'reports/summary.docx',
  ])
})

test('filters by path, case-insensitively', async ({ page }) => {
  await openView(page)

  await page.getByRole('textbox', { name: 'Search' }).fill('REPORTS')

  await expect(documentLinks(page)).toHaveCount(1)
  await expect(documentLinks(page)).toContainText('reports/summary.docx')
})

test('opens a document in Collabora in a new tab', async ({ page }) => {
  await openView(page)

  const link = page.getByRole('link', {
    name: 'reports/summary.docx: edit in writer (opens in a new tab)',
  })
  await expect(link).toHaveAttribute('target', '_blank')
  await expect(link).toHaveAttribute('href', /\/collabora\/browser\/.*WOPISrc=/)
})

test('tells an empty search result apart and clears the search', async ({ page }) => {
  await openView(page)

  await page.getByRole('textbox', { name: 'Search' }).fill('missing')
  await expect(page.getByText('No matching documents')).toBeVisible()

  await page.getByRole('button', { name: 'Clear search', exact: true }).click()
  await expect(documentLinks(page)).toHaveCount(3)
})

test('shows an empty state when MinIO holds no documents', async ({ page }) => {
  await openView(page, [])

  await expect(page.getByText('No documents yet')).toBeVisible()
})

test('shows a loading indicator until the first list arrives', async ({ page }) => {
  await installMockBackend(page)
  let release!: () => void
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/documents/refresh', async (route) => {
    await held
    await route.fulfill({ json: null })
  })
  await page.goto('/')

  await expect(page.getByRole('progressbar', { name: 'Loading documents' })).toBeVisible()
  release()
  await expect(documentLinks(page)).toHaveCount(3)
})
