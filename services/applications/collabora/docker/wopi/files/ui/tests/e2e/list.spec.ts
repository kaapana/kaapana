import { test, expect } from '@playwright/test'
import { breadcrumbs, documentLinks, folder, openView, rows } from './fixtures/helpers'
import { documentEntry, installMockBackend } from './fixtures/mock-backend'

test('loads the documents with a single request on open', async ({ page }) => {
  const calls: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('/documents/')) calls.push(`${r.method()} ${new URL(r.url()).pathname}`)
  })
  await openView(page)

  expect(calls).toEqual(['GET /documents/'])
})

test('shows the top-level folders before the files, sorted by name', async ({ page }) => {
  await openView(page)

  await expect(rows(page)).toHaveCount(3)
  await expect(rows(page)).toContainText(['notes', 'reports', 'welcome.odt'])
  await expect(breadcrumbs(page)).toHaveText('Documents')
})

test('summarises a folder by its document count and latest change', async ({ page }) => {
  await openView(page)

  const reports = rows(page).filter({ has: folder(page, 'reports') })
  await expect(reports).toContainText('2 documents')
  await expect(reports).toContainText('Oct 1, 2026')
})

test('opens folders and walks back through the breadcrumbs', async ({ page }) => {
  await openView(page)

  await folder(page, 'reports').click()
  await expect(rows(page)).toContainText(['2026', 'summary.docx'])
  await expect(breadcrumbs(page)).toContainText('reports')

  await folder(page, '2026').click()
  await expect(rows(page)).toHaveCount(1)
  await expect(rows(page)).toContainText('q3.xlsx')

  await breadcrumbs(page).getByRole('button', { name: 'reports' }).click()
  await expect(rows(page)).toContainText(['2026', 'summary.docx'])
  await breadcrumbs(page).getByRole('button', { name: 'Documents' }).click()
  await expect(rows(page)).toContainText(['notes', 'reports', 'welcome.odt'])
})

test('marks the current folder in the breadcrumbs', async ({ page }) => {
  await openView(page)
  await folder(page, 'notes').click()

  await expect(breadcrumbs(page).locator('[aria-current="location"]')).toHaveText('notes')
  await expect(breadcrumbs(page).getByRole('button', { name: 'notes' })).toHaveCount(0)
})

test('opens folders with the keyboard', async ({ page }) => {
  await openView(page)

  await folder(page, 'notes').focus()
  await page.keyboard.press('Enter')

  await expect(rows(page)).toContainText('protocol.odt')
})

test('shows the modification date and size of a document', async ({ page }) => {
  await openView(page)

  const welcome = rows(page).filter({ hasText: 'welcome.odt' })
  await expect(welcome).toContainText('Sep 20, 2026')
  await expect(welcome).toContainText('1.0 KB')
})

test('sorts by last modified, folders still first', async ({ page }) => {
  await openView(page, [
    ...['a.docx', 'b.docx'].map((name, i) =>
      documentEntry(name, `2026-10-0${i + 1}T09:00:00+00:00`),
    ),
    documentEntry('archive/old.odt', '2026-01-01T09:00:00+00:00'),
  ])

  await expect(rows(page)).toContainText(['archive', 'a.docx', 'b.docx'])
  await page.locator('.v-select').click()
  await page.getByRole('option', { name: 'Last modified' }).click()

  await expect(rows(page)).toContainText(['archive', 'b.docx', 'a.docx'])
  await expect(documentLinks(page).first()).toContainText('b.docx')
})

test('sorts names naturally', async ({ page }) => {
  await openView(page, [
    documentEntry('report 10.docx', '2026-10-01T09:00:00+00:00'),
    documentEntry('report 9.docx', '2026-10-01T09:00:00+00:00'),
  ])

  await expect(rows(page)).toContainText(['report 9.docx', 'report 10.docx'])
})

test('searches all folders by path, case-insensitively', async ({ page }) => {
  await openView(page)
  await folder(page, 'notes').click()

  await page.getByRole('textbox', { name: 'Search' }).fill('REPORTS')

  await expect(breadcrumbs(page)).toBeHidden()
  await expect(page.getByRole('status')).toHaveText('2 documents in all folders')
  await expect(rows(page)).toContainText(['reports/2026/q3.xlsx', 'reports/summary.docx'])
})

test('returns to the folder when the search is cleared', async ({ page }) => {
  await openView(page)
  await folder(page, 'notes').click()
  await page.getByRole('textbox', { name: 'Search' }).fill('xlsx')

  await page.getByRole('textbox', { name: 'Search' }).fill('')

  await expect(breadcrumbs(page)).toContainText('notes')
  await expect(rows(page)).toContainText('protocol.odt')
})

test('opens a document in Collabora in a new tab', async ({ page }) => {
  await openView(page)
  await folder(page, 'reports').click()

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
  await expect(rows(page)).toHaveCount(3)
})

test('falls back to the closest folder that still exists after a reload', async ({ page }) => {
  const backend = await openView(page)
  await folder(page, 'reports').click()
  await folder(page, '2026').click()

  backend.documents = backend.documents.filter((doc) => doc.file.path !== 'reports/2026/q3.xlsx')
  await page.getByRole('button', { name: 'Refresh' }).click()

  await expect(breadcrumbs(page)).toContainText('reports')
  await expect(rows(page)).toHaveCount(1)
  await expect(rows(page)).toContainText('summary.docx')
})

test('shows an empty state when MinIO holds no documents', async ({ page }) => {
  await openView(page, [])

  await expect(page.getByText('No documents yet')).toBeVisible()
  await expect(breadcrumbs(page)).toBeHidden()
})

test('shows a loading indicator until the first list arrives', async ({ page }) => {
  const backend = await installMockBackend(page)
  let release!: () => void
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/documents/', async (route) => {
    await held
    await route.fulfill({ json: backend.documents })
  })
  await page.goto('/')

  await expect(page.getByRole('progressbar', { name: 'Loading documents' })).toBeVisible()
  release()
  await expect(rows(page)).toHaveCount(3)
})
