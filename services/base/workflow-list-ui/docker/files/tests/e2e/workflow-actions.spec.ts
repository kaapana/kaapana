import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

const WORKFLOW = /\/kaapana-backend\/client\/workflow(\?|$)/
const SYNC = /\/kaapana-backend\/client\/check-for-remote-updates/

// running-wf: automatic_execution true + not remote + not service -> abort/restart/delete.
function runningRow(page: import('@playwright/test').Page) {
  return page.getByRole('row').filter({ hasText: 'running-wf' })
}

test('abort workflow sends PUT /workflow with status "abort"', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const reqP = page.waitForRequest(
    (r) => WORKFLOW.test(r.url()) && r.method() === 'PUT',
  )
  await runningRow(page).locator('button:has(.mdi-stop-circle-outline)').click()
  const req = await reqP
  expect(req.postDataJSON()).toEqual({
    workflow_id: 'wf-running-001',
    workflow_status: 'abort',
  })
  await expect(
    page.getByText('Successfully aborted workflow wf-running-001 and all its local jobs'),
  ).toBeVisible()
})

test('restart workflow sends PUT /workflow with status "scheduled"', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const reqP = page.waitForRequest((r) => WORKFLOW.test(r.url()) && r.method() === 'PUT')
  await runningRow(page).locator('button:has(.mdi-rotate-left)').click()
  const req = await reqP
  expect(req.postDataJSON()).toEqual({
    workflow_id: 'wf-running-001',
    workflow_status: 'scheduled',
  })
})

test('delete workflow sends DELETE /workflow with the workflow_id', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const reqP = page.waitForRequest((r) => WORKFLOW.test(r.url()) && r.method() === 'DELETE')
  await runningRow(page).locator('button:has(.mdi-trash-can-outline)').click()
  const req = await reqP
  expect(req.url()).toContain('workflow_id=wf-running-001')
  await expect(page.getByText('Successfully deleted workflow wf-running-001')).toBeVisible()
})

test('manual-start (non-automatic workflow) sends PUT /workflow with status "confirmed"', async ({
  page,
}) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  // queued-wf has automatic_execution false -> the play (manual-start) button.
  const reqP = page.waitForRequest((r) => WORKFLOW.test(r.url()) && r.method() === 'PUT')
  await page
    .getByRole('row')
    .filter({ hasText: 'queued-wf' })
    .locator('button:has(.mdi-play-circle-outline)')
    .click()
  const req = await reqP
  expect(req.postDataJSON()).toEqual({
    workflow_id: 'wf-queued-004',
    workflow_status: 'confirmed',
  })
})

test('sync button triggers a remote-update check', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const reqP = page.waitForRequest((r) => SYNC.test(r.url()) && r.method() === 'GET')
  await page.locator('button:has(.mdi-sync)').click()
  await reqP
  await expect(page.getByText('Successfully checked for remote updates')).toBeVisible()
})

test('sync failure shows an error notification', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await installMockBackend(page)
  await page.route(SYNC, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: '{"detail":"remote unreachable"}',
    }),
  )
  await page.goto(VIEW_PATH)

  await page.locator('button:has(.mdi-sync)').click()

  await expect(page.getByText('Error while checking for remote updates')).toBeVisible()
  await expect(page.getByText('remote unreachable')).toBeVisible()
  expect(pageErrors).toEqual([])
})
