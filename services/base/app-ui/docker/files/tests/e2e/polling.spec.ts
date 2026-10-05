import { test, expect } from '@playwright/test'
import {
  boot,
  dialog,
  poll,
  prime,
  row,
  settle,
  defaultMockData,
  app,
  readyPod,
  pendingPod,
  errorPod,
} from './fixtures/mock-backend'

test('a pending app becomes openable after the next poll reports it ready', async ({ page }) => {
  const data = {
    ...defaultMockData,
    activeApplications: [
      app({ release_name: 'x1', name: 'Transitioner', pods: [pendingPod], ready: false }),
    ],
  }
  await boot(page, data)
  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Starting...' })).toBeVisible()

  // Backend now reports the pod running -> the next poll flips the affordance.
  data.activeApplications = [app({ release_name: 'x1', name: 'Transitioner', pods: [readyPod] })]
  await poll(page)

  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Open' })).toBeVisible()
  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Starting...' })).toHaveCount(
    0,
  )
})

test('an errored app recovers to ready across polls', async ({ page }) => {
  const data = {
    ...defaultMockData,
    activeApplications: [
      app({ release_name: 'x2', name: 'Recovering', pods: [errorPod], ready: false }),
    ],
  }
  await boot(page, data)
  await expect(row(page, 'Recovering').getByRole('button', { name: 'Error' })).toBeVisible()

  data.activeApplications = [app({ release_name: 'x2', name: 'Recovering', pods: [readyPod] })]
  await poll(page)

  await expect(row(page, 'Recovering').getByRole('button', { name: 'Open' })).toBeVisible()
})

// A failed poll must not throw away a list that already loaded, and must not
// toast every ten seconds either.
test('a failing poll keeps the last list and says so until a poll succeeds', async ({ page }) => {
  await prime(page)
  let failing = false
  await page.route(/\/kube-helm-api\/active-applications/, (r) => {
    if (failing) return r.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' })
    return r.fallback()
  })
  await settle(page)
  const alert = page.getByTestId('stale-list-alert')
  await expect(row(page, 'Segmentation Editor')).toBeVisible()

  failing = true
  for (let i = 0; i < 3; i++) {
    const responded = page.waitForResponse(/\/kube-helm-api\/active-applications/)
    await poll(page)
    await responded
  }
  await expect(alert).toContainText('Could not refresh the applications')
  await expect(row(page, 'Segmentation Editor')).toBeVisible()
  await expect(page.locator('.vue-notification')).toHaveCount(0)

  await alert.getByRole('button', { name: 'Details' }).click()
  await expect(dialog(page).locator('dd').first()).toContainText('500')
  await dialog(page).getByRole('button', { name: 'Close' }).click()

  failing = false
  await poll(page)
  await expect(alert).toHaveCount(0)
})
