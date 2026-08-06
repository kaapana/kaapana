import { test, expect } from '@playwright/test'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

const WORKFLOWS = /\/kaapana-backend\/client\/workflows(\?|$)/

test('search sends the query to the backend as a "search" param', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('running-wf', { exact: true })).toBeVisible()

  const reqP = page.waitForRequest(
    (r) => WORKFLOWS.test(r.url()) && r.url().includes('search=running'),
  )
  await page.getByLabel('Search for Workflow').fill('running')
  const req = await reqP
  expect(req.url()).toContain('search=running')
})

test('paging forward requests the next offset', async ({ page }) => {
  // 25 total with the default 10 per page -> a next page exists.
  await installMockBackend(page, { ...defaultMockData, totalWorkflows: 25 })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('running-wf', { exact: true })).toBeVisible()

  const reqP = page.waitForRequest(
    (r) => WORKFLOWS.test(r.url()) && r.url().includes('offset=10'),
  )
  await page.getByLabel('Next page').click()
  const req = await reqP
  expect(req.url()).toContain('offset=10')
  expect(req.url()).toContain('limit=10')
})
