import { test, expect } from '@playwright/test'
import { failRoute, openLogs, toasts } from './fixtures/helpers'
import { defaultMockData, logLine, run } from './fixtures/mock-backend'

test.describe('logs page', () => {
  test('selecting a task shows its log', async ({ page }) => {
    await openLogs(page, 1)
    await page.getByTestId('task-list').getByText('export', { exact: true }).click()
    await expect(page.getByTestId('log-output')).toContainText('Export finished')
    await expect(page.getByTestId('log-output')).not.toContainText('Loading dataset')
  })

  test('the severity chips filter the lines', async ({ page }) => {
    await openLogs(page, 1)
    const output = page.getByTestId('log-output')
    await page.getByText('INFO · 2').click()
    await expect(output).toContainText('Low contrast in slice 12')
    await expect(output).not.toContainText('Loading dataset')
  })

  test('searching all logs counts matches per task and jumps to them', async ({ page }) => {
    await openLogs(page, 1)
    await page.getByRole('textbox', { name: 'Search all logs' }).fill('export')
    const tasks = page.getByTestId('task-list')
    await expect(tasks.getByLabel('2 matches')).toBeVisible()
    // The selected task has no match, so the first task with matches opens.
    await expect(page.getByTestId('log-output')).toContainText('Exporting to nifti')
    await expect(page.getByTestId('log-output').locator('mark').first()).toHaveText(/export/i)
    await expect(page.getByText('Match 1 of 2')).toBeVisible()
    await page.getByRole('button', { name: 'Next match' }).click()
    await expect(page.getByText('Match 2 of 2')).toBeVisible()
  })

  test('log text is escaped, not rendered as HTML', async ({ page }) => {
    const data = defaultMockData()
    data.logs[11] = [logLine('<img src=x onerror="window.__xss=1">')]
    await openLogs(page, 1, { data })
    await expect(page.getByTestId('log-output')).toContainText('<img src=x')
    expect(await page.evaluate(() => (window as any).__xss)).toBeUndefined()
  })

  test('a failed log load says so and offers a retry', async ({ page }) => {
    let fail = true
    await openLogs(page, 1, {
      routes: (p) =>
        p.route(/task-runs\/11\/logs$/, (r) =>
          fail ? r.fulfill({ status: 500, body: '{}' }) : r.fallback(),
        ),
    })
    await expect(page.getByTestId('log-output')).toContainText(
      'The logs of this task could not be loaded.',
    )
    fail = false
    await page.getByTestId('log-output').getByRole('button', { name: 'Try again' }).click()
    await expect(page.getByTestId('log-output')).toContainText('Loading dataset lung-ct')
  })

  test('a failed download is reported', async ({ page }) => {
    await openLogs(page, 1)
    await expect(page.getByTestId('log-output')).toContainText('Loading dataset')
    await failRoute(page, /task-runs\/11\/logs$/, 'Log store offline')
    await page.getByRole('button', { name: 'Download log' }).click()
    await expect(toasts(page)).toContainText('Could not download the log')
  })

  test('downloading all logs produces one ZIP file', async ({ page }) => {
    await openLogs(page, 1)
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Download all logs' }).click()
    expect((await download).suggestedFilename()).toBe('Segmentation-v2-run-1-logs.zip')
  })

  test('the parameters the run was started with are shown per task', async ({ page }) => {
    await openLogs(page, 1)
    const panel = page.getByTestId('run-parameters')
    await panel.getByRole('button', { name: /Parameters/ }).click()

    await expect(panel).toContainText('segment')
    await expect(panel.locator('dt', { hasText: 'Dataset' }).locator('+ dd')).toHaveText('lung-ct')
    await expect(panel.locator('dt', { hasText: 'Threshold' }).locator('+ dd')).toHaveText('7')
    await expect(panel.locator('dt', { hasText: 'Format' }).locator('+ dd')).toHaveText('Not set')
    await expect(panel).toContainText('When the run completes successfully')
  })

  test('a run without parameters says so', async ({ page }) => {
    await openLogs(page, 3)
    const panel = page.getByTestId('run-parameters')
    await expect(panel).toContainText('(none)')
    await panel.getByRole('button', { name: /Parameters/ }).click()
    await expect(panel).toContainText('This run was started without parameters.')
  })

  test('a run without tasks explains that nothing has started', async ({ page }) => {
    const data = defaultMockData()
    data.runs.push(run({ id: 9, task_runs: [] }))
    await openLogs(page, 9, { data })
    await expect(page.getByText('No tasks have started yet')).toBeVisible()
  })

  test('an unknown run says so and leads back to the list', async ({ page }) => {
    await openLogs(page, 404)
    await expect(page.getByText('Run 404 does not exist')).toBeVisible()
    await page.getByRole('link', { name: 'Back to workflow runs' }).click()
    await expect(page).toHaveURL(/\/workflow-ui\/runs$/)
  })

  test('every toolbar control has an accessible name', async ({ page }) => {
    await openLogs(page, 1)
    for (const name of ['Reload log', 'Copy log', 'Download log', 'Download all logs']) {
      await expect(page.getByRole('button', { name, exact: true })).toBeVisible()
    }
    await expect(page.getByLabel('Color by severity')).toBeVisible()
  })
})
