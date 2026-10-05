import { test, expect, type Page } from '@playwright/test'
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
  TASKS_PATH,
  type MockData,
} from './fixtures/mock-backend'

test('a pending app becomes openable after the next poll reports it ready', async ({ page }) => {
  const data = {
    ...defaultMockData,
    activeApplications: [
      app({ release_name: 'x1', displayName: 'Transitioner', pods: [pendingPod], ready: false }),
    ],
  }
  await boot(page, data)
  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Starting...' })).toBeVisible()

  // Backend now reports the pod running -> the next poll flips the affordance.
  data.activeApplications = [
    app({ release_name: 'x1', displayName: 'Transitioner', pods: [readyPod] }),
  ]
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
      app({ release_name: 'x2', displayName: 'Recovering', pods: [errorPod], ready: false }),
    ],
  }
  await boot(page, data)
  await expect(row(page, 'Recovering').getByRole('button', { name: 'Error' })).toBeVisible()

  data.activeApplications = [
    app({ release_name: 'x2', displayName: 'Recovering', pods: [readyPod] }),
  ]
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

test.describe('embedded in the shell', () => {
  async function openEmbedded(page: Page, data: MockData) {
    await prime(page, data)
    await page.route('**/shell-harness', (r) =>
      r.fulfill({
        status: 200,
        contentType: 'text/html',
        body: `<!doctype html><html><body><script>
                 window.__msgs = []
                 addEventListener('message', (e) => window.__msgs.push(e.data))
               </script><iframe src="${TASKS_PATH}" style="width:1280px;height:900px;border:0"></iframe></body></html>`,
      }),
    )
    await page.goto('/shell-harness')
    return page.frameLocator('iframe')
  }
  const messages = (page: Page) =>
    page.evaluate(() => (window as unknown as { __msgs: unknown[] }).__msgs)

  async function pollAndWait(page: Page) {
    const responded = page.waitForResponse(/\/kube-helm-api\/active-applications/)
    await poll(page)
    await responded
  }

  test('a changed task list asks the shell to refresh its badge', async ({ page }) => {
    const data = structuredClone(defaultMockData)
    const view = await openEmbedded(page, data)
    await expect(
      view.locator('.v-list-item').filter({ hasText: 'Segmentation Editor' }),
    ).toBeVisible()

    await pollAndWait(page)
    expect(await messages(page)).toEqual([])

    data.activeApplications = data.activeApplications.filter(
      (a) => a.release_name !== 'seg-editor-1a2b',
    )
    await pollAndWait(page)
    await expect.poll(() => messages(page)).toEqual([{ type: 'kaapana:shell-refresh' }])

    await pollAndWait(page)
    expect(await messages(page)).toEqual([{ type: 'kaapana:shell-refresh' }])
  })

  test('a change to project-wide applications does not refresh the shell', async ({ page }) => {
    const data = structuredClone(defaultMockData)
    const view = await openEmbedded(page, data)
    await expect(
      view.locator('.v-list-item').filter({ hasText: 'Segmentation Editor' }),
    ).toBeVisible()

    data.activeApplications = data.activeApplications.filter((a) => a.from_workflow_run)
    await pollAndWait(page)
    await pollAndWait(page)
    expect(await messages(page)).toEqual([])
  })
})
