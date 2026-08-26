import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

const JOB = /\/kaapana-backend\/client\/job(\?|$)/
const TASKINSTANCES = /\/kaapana-backend\/client\/get-job-taskinstances/

// job 101 (dag-alpha) is a local job (instance_name === owner) -> abort/restart/delete.
async function expandRunningWorkflow(page: import('@playwright/test').Page) {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await page.getByText('running-wf', { exact: true }).click()
  await expect(page.getByText('dag-alpha')).toBeVisible()
}

function jobRow(page: import('@playwright/test').Page) {
  // The job table is nested inside a <td> of the workflow table's expanded row;
  // scope to it so the outer wrapper row isn't also matched.
  return page.locator('td .v-data-table').getByRole('row').filter({ hasText: 'dag-alpha' })
}

function failedJobRow(page: import('@playwright/test').Page) {
  return page.locator('td .v-data-table').getByRole('row').filter({ hasText: 'dag-beta' })
}

function fail500(page: import('@playwright/test').Page, url: RegExp) {
  return page.route(url, (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' }),
  )
}

test('abort job sends PUT /job with status "abort"', async ({ page }) => {
  await expandRunningWorkflow(page)

  const reqP = page.waitForRequest((r) => JOB.test(r.url()) && r.method() === 'PUT')
  await jobRow(page).locator('button:has(.mdi-stop-circle-outline)').click()
  const req = await reqP
  expect(req.postDataJSON()).toMatchObject({ job_id: 101, status: 'abort' })
})

test('restart job sends PUT /job with status "scheduled"', async ({ page }) => {
  await expandRunningWorkflow(page)

  const reqP = page.waitForRequest((r) => JOB.test(r.url()) && r.method() === 'PUT')
  await jobRow(page).locator('button:has(.mdi-rotate-left)').click()
  const req = await reqP
  expect(req.postDataJSON()).toMatchObject({ job_id: 101, status: 'scheduled' })
})

test('delete job sends DELETE /job with the job_id', async ({ page }) => {
  await expandRunningWorkflow(page)

  const reqP = page.waitForRequest((r) => JOB.test(r.url()) && r.method() === 'DELETE')
  await jobRow(page).locator('button:has(.mdi-trash-can-outline)').click()
  const req = await reqP
  expect(req.url()).toContain('job_id=101')
})

test('abort job failure shows an error toast and keeps the job rows', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await expandRunningWorkflow(page)
  await fail500(page, JOB)

  await jobRow(page).locator('button:has(.mdi-stop-circle-outline)').click()

  await expect(page.getByText('Error while aborting job 101')).toBeVisible()
  await expect(page.getByText('boom')).toBeVisible()
  await expect(page.getByText('dag-alpha')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('restart job failure shows an error toast and keeps the job rows', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await expandRunningWorkflow(page)
  await fail500(page, JOB)

  await jobRow(page).locator('button:has(.mdi-rotate-left)').click()

  await expect(page.getByText('Error while restarting job 101')).toBeVisible()
  await expect(page.getByText('dag-alpha')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('delete job failure shows an error toast and keeps the job rows', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await expandRunningWorkflow(page)
  await fail500(page, JOB)

  await jobRow(page).locator('button:has(.mdi-trash-can-outline)').click()

  await expect(page.getByText('Error while deleting job 101')).toBeVisible()
  await expect(page.getByText('dag-alpha')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('failed-operator logs: a task-instance fetch failure toasts instead of opening a tab', async ({
  page,
}) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await expandRunningWorkflow(page)
  await fail500(page, TASKINSTANCES)

  // job 102 (dag-beta) is failed -> it has the failed-operator logs button.
  await failedJobRow(page).locator('button:has(.mdi-alert-decagram-outline)').click()

  await expect(page.getByText('Error while loading task instances of job 102')).toBeVisible()
  await expect(page.getByText('boom')).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('failed-operator logs: a failed job with no failed task warns instead of crashing', async ({
  page,
}) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })
  // The default mock returns {} for get-job-taskinstances: a successful fetch
  // with no task whose last state is 'failed'.
  await expandRunningWorkflow(page)

  await failedJobRow(page).locator('button:has(.mdi-alert-decagram-outline)').click()

  await expect(page.getByText('No failed operator found for job 102')).toBeVisible()
  expect(pageErrors).toEqual([])
  // Match the error NAME - the message wording is engine-version specific.
  expect(consoleErrors.filter((t) => /TypeError/.test(t))).toEqual([])
})
