import { test, expect } from '@playwright/test'
import { defaultMockData, installMockBackend, seedShellState, VIEW_PATH } from './fixtures/mock-backend'

test('reports an error and shows an empty tree when the results endpoint errors', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Later route wins: fail every tree request with a 500.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  )
  await page.goto(VIEW_PATH)

  await expect(page.getByText('The workflow results could not be loaded.')).toBeVisible()
  // View still mounts; nothing loaded, so the tree stays empty.
  await expect(page.getByRole('textbox', { name: 'Search loaded results' })).toBeVisible()
  await expect(page.locator('.v-treeview .v-list-item')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Workflow results' })).toBeVisible()
})

test('a failed folder expansion reports the error and leaves the folder without children', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Fail only prefixed (child) requests; defer the root request to the mock.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    if (new URL(r.request().url()).searchParams.get('prefix')) {
      return r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) })
    }
    return r.fallback()
  })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()

  const childReq = page.waitForRequest((r) => r.url().includes('prefix=nnunet-training-230101'))
  await page.getByText('nnunet-training-230101').click()
  await childReq

  await expect(page.getByText('The folder contents could not be loaded.')).toBeVisible()
  // The folder remains, but no children appear.
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()
  await expect(page.getByText('report.html')).toHaveCount(0)
})

test('a failed "Load more root results" reports the error and keeps the loaded rows', async ({ page }) => {
  const data = structuredClone(defaultMockData)
  data.root.nextContinuationToken = 'root-page-2'
  const pageErrors: Error[] = []
  page.on('pageerror', (error) => pageErrors.push(error))
  await seedShellState(page)
  await installMockBackend(page, data)
  // Later route wins: fail only the continuation request.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    if (new URL(r.request().url()).searchParams.get('continuation_token')) {
      return r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) })
    }
    return r.fallback()
  })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()

  await page.getByRole('button', { name: 'Load more root results' }).click()

  await expect(page.getByText('The next page of results could not be loaded.')).toBeVisible()
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()
  // The token survives the failure, so the retry button is still there.
  await expect(page.getByRole('button', { name: 'Load more root results' })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a failed per-folder "Load more" reports the error and keeps the loaded children', async ({ page }) => {
  const data = structuredClone(defaultMockData)
  data.children['nnunet-training-230101/'].nextContinuationToken = 'nnunet-page-2'
  await seedShellState(page)
  await installMockBackend(page, data)
  // Later route wins: fail only the continuation request.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    if (new URL(r.request().url()).searchParams.get('continuation_token')) {
      return r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) })
    }
    return r.fallback()
  })
  await page.goto(VIEW_PATH)
  await page.getByText('nnunet-training-230101').click()
  await expect(page.getByText('report.html')).toBeVisible()

  await page.getByRole('button', { name: 'Load more', exact: true }).click()

  await expect(page.getByText('The next page of folder results could not be loaded.')).toBeVisible()
  await expect(page.getByText('report.html')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Load more', exact: true })).toBeVisible()
})
