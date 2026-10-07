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
    .getByRole('button', { name: 'Show the configuration of this job' })
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

test("a slow job fetch does not overwrite the row the user switched to", async ({ page }) => {
  await installMockBackend(page)

  // running-wf answers only after failed-wf has already been served, which is
  // the order the component used to accept blindly.
  let releaseSlow: () => void = () => {}
  const slowReleased = new Promise<void>((resolve) => {
    releaseSlow = resolve
  })
  await page.route(/\/kaapana-backend\/client\/jobs(\?|$)/, async (route) => {
    const name = new URL(route.request().url()).searchParams.get('workflow_name')
    const dag = name === 'running-wf' ? 'dag-of-running' : 'dag-of-failed'
    if (name === 'running-wf') await slowReleased
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          status: 'finished',
          description: '{}',
          conf_data: {},
          time_created: '2026-07-20T10:00:00',
          time_updated: '2026-07-20T10:01:00',
          dag_id: dag,
          run_id: `run-${dag}`,
          kaapana_instance: { instance_name: 'local', remote: false },
          owner_kaapana_instance_name: 'local',
          external_job_id: null,
          service_job: false,
        },
      ]),
    })
  })

  await page.goto(VIEW_PATH)
  await page.getByText('running-wf', { exact: true }).click()
  await page.getByText('failed-wf', { exact: true }).click()
  await expect(page.getByText('dag-of-failed')).toBeVisible()

  releaseSlow()
  await expect(page.getByText('dag-of-running')).toHaveCount(0)
  await expect(page.getByText('dag-of-failed')).toBeVisible()
})
