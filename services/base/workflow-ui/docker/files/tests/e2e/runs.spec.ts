import { test, expect } from '@playwright/test'
import {
  countRequests,
  dialog,
  failRoute,
  openFailureDetails,
  openRuns,
  runRow,
  runRows,
  toasts,
} from './fixtures/helpers'
import { defaultMockData, run, RUNS_PATH, taskRun } from './fixtures/mock-backend'
import { WorkflowRunStatus } from '../../src/types/schemas'

test.describe('run list', () => {
  test('runs are sorted newest first and show status, workflow and run id', async ({ page }) => {
    await openRuns(page)
    await expect(runRows(page)).toHaveCount(3)
    await expect(runRows(page).nth(0)).toContainText('Running')
    await expect(runRows(page).nth(0)).toContainText('v2 · Run 2')
    await expect(runRows(page).nth(1)).toContainText('Registration')
    await expect(runRows(page).nth(2)).toContainText('Completed')
  })

  test('the cleanup state of a run is shown', async ({ page }) => {
    const data = defaultMockData()
    data.runs[0] = { ...data.runs[0], cleanup_status: 'cleaned' }
    await openRuns(page, { data })
    await expect(runRow(page, 1)).toContainText('Data cleaned')
    await expect(runRow(page, 1).getByRole('button', { name: 'Clean run data' })).toHaveCount(0)
  })

  test('only applicable actions are offered', async ({ page }) => {
    await openRuns(page)
    const running = runRow(page, 2)
    await expect(running.getByRole('button', { name: 'Cancel run' })).toBeVisible()
    await expect(running.getByRole('button', { name: 'Retry run' })).toHaveCount(0)
    await expect(running.getByRole('button', { name: 'Delete run' })).toHaveCount(0)
    await expect(running.getByRole('button', { name: 'Clean run data' })).toHaveCount(0)

    const failed = runRow(page, 3)
    await expect(failed.getByRole('button', { name: 'Retry run' })).toBeVisible()
    await expect(failed.getByRole('button', { name: 'Delete run' })).toBeVisible()
    await expect(failed.getByRole('button', { name: 'Cancel run' })).toHaveCount(0)
    // One task: no ZIP of all logs.
    await expect(failed.getByRole('button', { name: 'Download all logs (ZIP)' })).toHaveCount(0)

    const completed = runRow(page, 1)
    await expect(completed.getByRole('button', { name: 'Retry run' })).toHaveCount(0)
    await expect(completed.getByRole('button', { name: 'Delete run' })).toBeVisible()
    await expect(completed.getByRole('button', { name: 'Download all logs (ZIP)' })).toBeVisible()
  })

  test('a canceled run can be retried', async ({ page }) => {
    const data = defaultMockData()
    data.runs.push(run({ id: 7, lifecycle_status: WorkflowRunStatus.CANCELED }))
    await openRuns(page, { data })
    await expect(runRow(page, 7).getByRole('button', { name: 'Retry run' })).toBeVisible()
  })

  test('a run canceled before it reached the engine cannot be retried', async ({ page }) => {
    const data = defaultMockData()
    data.runs.push(run({ id: 7, lifecycle_status: WorkflowRunStatus.CANCELED, external_id: null }))
    await openRuns(page, { data })
    await expect(runRow(page, 7).getByRole('button', { name: 'Retry run' })).toHaveCount(0)
    await expect(runRow(page, 7).getByRole('button', { name: 'Delete run' })).toBeVisible()
  })

  test('a failed run whose data was cleaned cannot be retried', async ({ page }) => {
    const data = defaultMockData()
    data.runs[2] = { ...data.runs[2], cleanup_status: 'cleaned' }
    await openRuns(page, { data })
    await expect(runRow(page, 3).getByRole('button', { name: 'Retry run' })).toHaveCount(0)
    await expect(runRow(page, 3).getByRole('button', { name: 'Delete run' })).toBeVisible()
  })

  test('a run with a cleanup in progress cannot be deleted', async ({ page }) => {
    const data = defaultMockData()
    data.runs[0] = { ...data.runs[0], cleanup_status: 'running' }
    await openRuns(page, { data })
    await expect(runRow(page, 1)).toContainText('Cleaning')
    await expect(runRow(page, 1).getByRole('button', { name: 'Delete run' })).toHaveCount(0)
  })

  test('a run that has not started yet can be canceled', async ({ page }) => {
    const data = defaultMockData()
    data.runs.push(run({ id: 7, lifecycle_status: WorkflowRunStatus.CREATED, external_id: null }))
    await openRuns(page, { data })
    await expect(runRow(page, 7).getByRole('button', { name: 'Retry run' })).toHaveCount(0)
    await runRow(page, 7).getByRole('button', { name: 'Cancel run' }).click()
    await dialog(page).getByRole('button', { name: 'Cancel run' }).click()
    await expect(runRow(page, 7)).toContainText('Canceled')
  })

  test('view logs opens the logs page of the run', async ({ page }) => {
    await openRuns(page)
    await runRow(page, 3).getByRole('button', { name: 'View logs' }).click()
    await expect(page).toHaveURL(/\/runs\/3\/logs$/)
    await expect(page.getByTestId('log-output')).toContainText('Fixed image is missing')
    await page.getByRole('link', { name: 'Workflow runs' }).click()
    await expect(page).toHaveURL(new RegExp(`${RUNS_PATH}$`))
  })
})

test.describe('run actions', () => {
  test('cancelling asks first, with the safe action focused', async ({ page }) => {
    await openRuns(page)
    const cancels = countRequests(page, /\/cancel$/)
    await runRow(page, 2).getByRole('button', { name: 'Cancel run' }).click()

    const confirm = dialog(page)
    await expect(confirm).toContainText('Cancel run 2?')
    await expect(confirm).toContainText('Running tasks are aborted')
    await expect(confirm.getByRole('button', { name: 'Keep running' })).toBeFocused()
    await confirm.getByRole('button', { name: 'Keep running' }).click()
    await expect(dialog(page)).toHaveCount(0)
    expect(cancels()).toBe(0)
  })

  test('a confirmed cancel updates the row and reports success', async ({ page }) => {
    await openRuns(page)
    await runRow(page, 2).getByRole('button', { name: 'Cancel run' }).click()
    await dialog(page).getByRole('button', { name: 'Cancel run' }).click()
    await expect(runRow(page, 2)).toContainText('Canceled')
    await expect(toasts(page)).toContainText('Run canceled')
  })

  test('retry sends a failed run back to the engine without asking', async ({ page }) => {
    await openRuns(page)
    await runRow(page, 3).getByRole('button', { name: 'Retry run' }).click()
    await expect(runRow(page, 3)).toContainText('Pending')
    await expect(toasts(page)).toContainText('Run retried')
  })

  test('a retry the service refuses shows its reason', async ({ page }) => {
    const recorder = await openRuns(page)
    recorder.data.runs = recorder.data.runs.map((r) =>
      r.id === 3 ? { ...r, cleanup_status: 'cleaned' } : r,
    )
    await runRow(page, 3).getByRole('button', { name: 'Retry run' }).click()
    await expect(toasts(page)).toContainText('Could not retry the run')
    await expect(toasts(page)).toContainText('The data of run 3 was cleaned')
    await expect(runRow(page, 3)).toContainText('Error')
  })

  test('a cancel of a run that finished meanwhile shows the reason', async ({ page }) => {
    const recorder = await openRuns(page)
    recorder.data.runs = recorder.data.runs.map((r) =>
      r.id === 2 ? { ...r, lifecycle_status: WorkflowRunStatus.COMPLETED } : r,
    )
    await runRow(page, 2).getByRole('button', { name: 'Cancel run' }).click()
    await dialog(page).getByRole('button', { name: 'Cancel run' }).click()
    await expect(toasts(page)).toContainText('Run 2 is Completed and cannot be canceled.')
  })

  test('a failed action explains what failed and offers details', async ({ page }) => {
    await openRuns(page)
    await failRoute(page, /\/workflow-runs\/3\/retry$/, 'Engine unreachable', 502)
    await runRow(page, 3).getByRole('button', { name: 'Retry run' }).click()
    const details = await openFailureDetails(page, 'Could not retry the run')
    await expect(details).toContainText('Engine unreachable')
    await expect(details).toContainText('502')
  })

  test('cleaning one run confirms as a destructive action', async ({ page }) => {
    await openRuns(page)
    await runRow(page, 1).getByRole('button', { name: 'Clean run data' }).click()
    const confirm = dialog(page)
    await expect(confirm).toContainText('Clean the data of run 1?')
    await expect(confirm).toContainText('This cannot be undone.')
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    await expect(confirm.getByRole('button', { name: 'Clean data' })).toHaveClass(/text-error/)
    await confirm.getByRole('button', { name: 'Clean data' }).click()
    await expect(runRow(page, 1)).toContainText('Cleanup pending')
  })

  test('deleting a run confirms as a destructive action', async ({ page }) => {
    await openRuns(page)
    const deletes = countRequests(page, /\/workflow-runs\/3$/)
    await runRow(page, 3).getByRole('button', { name: 'Delete run' }).click()
    const confirm = dialog(page)
    await expect(confirm).toContainText('Delete run 3?')
    await expect(confirm).toContainText('This cannot be undone.')
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    await expect(confirm.getByRole('button', { name: 'Delete run' })).toHaveClass(/text-error/)
    await confirm.getByRole('button', { name: 'Cancel' }).click()
    await expect(runRows(page)).toHaveCount(3)
    expect(deletes()).toBe(0)
  })

  test('a confirmed delete removes the run', async ({ page }) => {
    const recorder = await openRuns(page)
    await runRow(page, 3).getByRole('button', { name: 'Delete run' }).click()
    await dialog(page).getByRole('button', { name: 'Delete run' }).click()
    await expect(toasts(page)).toContainText('Run deleted')
    await expect(runRows(page)).toHaveCount(2)
    await expect(runRow(page, 3)).toHaveCount(0)
    expect(recorder.data.runs.map((r) => r.id)).not.toContain(3)
  })

  test('a refresh that started before an action does not undo it', async ({ page }) => {
    let release: () => void = () => {}
    const recorder = await openRuns(page)
    await page.route('**/workflow-api/v1/workflow-runs', async (r) => {
      const stale = JSON.stringify(recorder.data.runs)
      await new Promise<void>((resolve) => (release = resolve))
      await r.fulfill({ contentType: 'application/json', body: stale })
    })
    await page.getByRole('button', { name: 'Refresh' }).click()
    await runRow(page, 3).getByRole('button', { name: 'Delete run' }).click()
    await dialog(page).getByRole('button', { name: 'Delete run' }).click()
    await expect(runRow(page, 3)).toHaveCount(0)
    release()
    await expect(page.getByRole('button', { name: 'Refresh' })).not.toHaveClass(/v-btn--loading/)
    await expect(runRows(page)).toHaveCount(2)
    await expect(runRow(page, 3)).toHaveCount(0)
  })

  test('runs being cleaned in bulk cannot be deleted meanwhile', async ({ page }) => {
    let release: () => void = () => {}
    await openRuns(page, {
      routes: (p) =>
        p.route(/\/workflow-runs\/1\/clean$/, async (r) => {
          await new Promise<void>((resolve) => (release = resolve))
          await r.fallback()
        }),
    })
    await page.getByRole('button', { name: 'Clean finished runs' }).click()
    await dialog(page).getByRole('button', { name: 'Clean data' }).click()
    await expect(runRow(page, 1).getByRole('button', { name: 'Delete run' })).toBeDisabled()
    release()
    await expect(runRow(page, 1)).toContainText('Cleanup pending')
  })

  test('a failed delete keeps the run', async ({ page }) => {
    await openRuns(page)
    await failRoute(page, /\/workflow-runs\/3$/, 'Engine unreachable', 502)
    await runRow(page, 3).getByRole('button', { name: 'Delete run' }).click()
    await dialog(page).getByRole('button', { name: 'Delete run' }).click()
    await expect(toasts(page)).toContainText('Could not delete the run')
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('bulk cleanup counts the eligible runs and cleans each of them', async ({ page }) => {
    const recorder = await openRuns(page)
    await page.getByRole('button', { name: 'Clean finished runs' }).click()
    await expect(dialog(page)).toContainText('Clean the data of 2 finished runs?')
    await dialog(page).getByRole('button', { name: 'Clean data' }).click()
    await expect(toasts(page)).toContainText('Data cleanup queued')
    expect(
      recorder.data.runs
        .filter((r) => r.cleanup_status === 'pending')
        .map((r) => r.id)
        .sort(),
    ).toEqual([1, 3])
  })
})

test.describe('run list states', () => {
  test('no runs yet points to the workflows', async ({ page }) => {
    await openRuns(page, { data: { ...defaultMockData(), runs: [] } })
    await expect(page.getByTestId('collection-state')).toContainText('No workflow runs yet')
    await expect(page.getByRole('button', { name: 'Open workflows' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clean finished runs' })).toBeDisabled()
  })

  test('a failed load shows an error with retry instead of an empty table', async ({ page }) => {
    let fail = true
    await openRuns(page, {
      routes: (p) =>
        p.route('**/workflow-api/v1/workflow-runs', (r) =>
          fail ? r.fulfill({ status: 500, body: '{}' }) : r.fallback(),
        ),
    })
    const state = page.getByTestId('collection-state')
    await expect(state).toContainText('Could not load the workflow runs')
    fail = false
    await state.getByRole('button', { name: 'Try again' }).click()
    await expect(runRows(page)).toHaveCount(3)
  })

  test('a refresh keeps the table visible', async ({ page }) => {
    let release: () => void = () => {}
    await openRuns(page)
    await page.route('**/workflow-api/v1/workflow-runs', async (r) => {
      await new Promise<void>((resolve) => (release = resolve))
      await r.fallback()
    })
    await page.getByRole('button', { name: 'Refresh' }).click()
    await expect(runRows(page)).toHaveCount(3)
    release()
  })
})

test.describe('automatic update', () => {
  test('the list reloads itself while a run is active', async ({ page }) => {
    await page.clock.install()
    const recorder = await openRuns(page)
    await expect(runRow(page, 2)).toContainText('Running')

    recorder.data.runs = recorder.data.runs.map((r) =>
      r.id === 2 ? { ...r, lifecycle_status: WorkflowRunStatus.COMPLETED } : r,
    )
    await page.clock.runFor(16_000)
    await expect(runRow(page, 2)).toContainText('Completed')
  })

  test('the list reloads itself while a cleanup is in progress', async ({ page }) => {
    await page.clock.install()
    const data = {
      ...defaultMockData(),
      runs: [run({ id: 1, cleanup_status: 'pending', task_runs: [taskRun(11, 1, 'segment')] })],
    }
    const recorder = await openRuns(page, { data })
    await expect(runRow(page, 1).getByRole('button', { name: 'Delete run' })).toHaveCount(0)

    recorder.data.runs = recorder.data.runs.map((r) => ({ ...r, cleanup_status: 'cleaned' }))
    await page.clock.runFor(16_000)
    await expect(runRow(page, 1)).toContainText('Data cleaned')
    await expect(runRow(page, 1).getByRole('button', { name: 'Delete run' })).toBeVisible()
  })

  test('nothing is polled when every run is finished', async ({ page }) => {
    await page.clock.install()
    const data = {
      ...defaultMockData(),
      runs: [run({ id: 1, task_runs: [taskRun(11, 1, 'segment')] })],
    }
    await openRuns(page, { data })
    await expect(runRows(page)).toHaveCount(1)
    const loads = countRequests(page, /\/workflow-runs$/)
    await page.clock.runFor(60_000)
    expect(loads()).toBe(0)
  })
})
