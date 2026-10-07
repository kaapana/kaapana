import { test, expect } from '@playwright/test'
import { card, openLogs, openRuns, openWorkflows, runRows } from './fixtures/helpers'
import { VIEW_BASE } from './fixtures/mock-backend'

test.describe('boot', () => {
  test('the workflows page lists one card per workflow without errors', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(String(e)))
    await openWorkflows(page)

    await expect(page.getByTestId('workflow-card')).toHaveCount(3)
    await expect(card(page, 'Segmentation')).toBeVisible()
    await expect(page).toHaveTitle('Workflows')
    expect(errors).toEqual([])
  })

  test('the runs page lists every run', async ({ page }) => {
    await openRuns(page)
    await expect(runRows(page)).toHaveCount(3)
    await expect(page).toHaveTitle('Workflow Runs')
  })

  test('the logs page shows the first task of the run', async ({ page }) => {
    await openLogs(page, 1)
    await expect(page.getByRole('heading', { name: 'Details of Segmentation v2' })).toBeVisible()
    await expect(page.getByTestId('log-output')).toContainText('Loading dataset lung-ct')
  })

  test('the view root redirects to the workflows page', async ({ page }) => {
    await openWorkflows(page)
    await page.goto(`${VIEW_BASE}/`)
    await expect(page).toHaveURL(/\/workflow-ui\/workflows$/)
  })
})
