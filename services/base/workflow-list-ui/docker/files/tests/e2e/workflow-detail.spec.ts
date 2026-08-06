import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

const JOBS = /\/kaapana-backend\/client\/jobs(\?|$)/

test('expanding a workflow fetches and renders its jobs', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const jobsReqP = page.waitForRequest((r) => JOBS.test(r.url()) && r.method() === 'GET')
  await page.getByText('running-wf', { exact: true }).click()

  const jobsReq = await jobsReqP
  expect(jobsReq.url()).toContain('workflow_name=running-wf')

  await expect(page.getByText('dag-alpha')).toBeVisible()
  await expect(page.getByText('dag-beta')).toBeVisible()
  await expect(page.getByRole('button', { name: 'running', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'failed', exact: true })).toBeVisible()
})

test('opening a job conf shows the conf-data dialog', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await page.getByText('running-wf', { exact: true }).click()
  await expect(page.getByText('dag-alpha')).toBeVisible()

  await page
    .locator('td .v-data-table')
    .getByRole('row')
    .filter({ hasText: 'dag-alpha' })
    .locator('.mdi-email')
    .click()

  await expect(page.getByText('Conf object')).toBeVisible()
  await expect(page.getByText('workflow_form')).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()
  await expect(page.getByText('Conf object')).toHaveCount(0)
})

test("a failing job fetch toasts and drops the previous workflow's jobs", async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await page.getByText('running-wf', { exact: true }).click()
  await expect(page.getByText('dag-alpha')).toBeVisible()

  await page.route(JOBS, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' }),
  )
  const failedReqP = page.waitForRequest(
    (r) => JOBS.test(r.url()) && r.url().includes('workflow_name=failed-wf'),
  )
  await page.getByText('failed-wf', { exact: true }).click()
  await failedReqP

  await expect(page.getByText('Error while loading jobs of workflow failed-wf')).toBeVisible()
  await expect(page.getByText('dag-alpha')).toHaveCount(0)
  expect(pageErrors).toEqual([])
})
