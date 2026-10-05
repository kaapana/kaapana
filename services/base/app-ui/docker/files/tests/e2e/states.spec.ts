import { test, expect } from '@playwright/test'
import {
  boot,
  dialog,
  failApplicationList,
  prime,
  row,
  settle,
  defaultMockData,
  APPS_PATH,
  TASKS_PATH,
} from './fixtures/mock-backend'

// A list that has not loaded yet is not an empty list.
test('the list shows a loading state before the first response arrives', async ({ page }) => {
  await prime(page)
  let release = () => {}
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route(/\/kube-helm-api\/active-applications/, async (r) => {
    await held
    return r.fallback()
  })
  await settle(page)

  await expect(page.locator('.v-skeleton-loader')).toBeVisible()
  await expect(page.locator('.v-empty-state')).toHaveCount(0)

  release()
  await expect(row(page, 'Segmentation Editor')).toBeVisible()
  await expect(page.locator('.v-skeleton-loader')).toHaveCount(0)
})

test('each route explains its empty list', async ({ page }) => {
  await boot(page, { ...defaultMockData, activeApplications: [] }, TASKS_PATH)
  await expect(page.locator('.v-empty-state')).toContainText(
    'No applications are waiting for your input',
  )

  await page.goto(APPS_PATH)
  await expect(page.locator('.v-empty-state')).toContainText('No applications in this project')
  await expect(page.locator('.v-empty-state')).toContainText(
    'No application is installed for project admin.',
  )
})

test('a failed first load is an error with a retry, not an empty list', async ({ page }) => {
  await prime(page)
  await failApplicationList(page)
  await settle(page)

  const state = page.locator('.v-empty-state')
  await expect(state).toContainText('Could not load the applications')
  await expect(page.getByText('No applications are waiting for your input')).toHaveCount(0)

  await state.getByRole('button', { name: 'Details' }).click()
  await expect(dialog(page)).toContainText('kube-helm is unreachable')
  await dialog(page).getByRole('button', { name: 'Close' }).click()

  await page.unroute(/\/kube-helm-api\/active-applications/)
  await installListAgain(page)
  await state.getByRole('button', { name: 'Try again' }).click()
  await expect(row(page, 'Segmentation Editor')).toBeVisible()
})

test('a failed project lookup is reported and fetches no applications', async ({ page }) => {
  const pageErrors: string[] = []
  const listRequests: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('request', (r) => {
    if (/kube-helm-api\/active-applications/.test(r.url())) listRequests.push(r.url())
  })

  await prime(page)
  // Admin realm role routes the project lookup to /aii/projects.
  await page.route('**/aii/projects', (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'boom' }),
    }),
  )
  await settle(page)

  await expect(page.locator('.v-empty-state')).toContainText('Could not load the project')
  // Without a project id every application would be filtered out.
  expect(listRequests).toEqual([])
  expect(pageErrors).toEqual([])
})

async function installListAgain(page: import('@playwright/test').Page) {
  await page.route(/\/kube-helm-api\/active-applications/, (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(defaultMockData.activeApplications),
    }),
  )
}
