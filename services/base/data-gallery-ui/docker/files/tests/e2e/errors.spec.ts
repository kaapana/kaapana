// Failure paths: a failed fetch must be reported once and leave the view usable.
import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, makeDefaultMockData, VIEW_PATH } from './fixtures/mock-backend'

function serverError(detail: string) {
  return {
    status: 500,
    contentType: 'application/json',
    body: JSON.stringify({ detail }),
  }
}

test('a ?dataset_name deep link reports a failing dataset list instead of "not found"', async ({
  page,
}) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await page.route(/\/kaapana-backend\/client\/datasets(\?.*)?$/, (r) =>
    r.fulfill(serverError('Datasets unavailable')),
  )

  await page.goto(`${VIEW_PATH}?dataset_name=nsclc`)

  await expect(page.getByText('Datasets unavailable').first()).toBeVisible()
  await expect(page.getByText('CT Thorax')).toBeVisible()
  await expect(page.getByText(/Dataset with name nsclc not found/)).toHaveCount(0)
  await expect(page.getByLabel('Select Dataset').first()).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

test('a failing values lookup skips only its own deep-link filter', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await page.route(/\/dataset\/query_values\/Modality$/, (r) =>
    r.fulfill(serverError('Values unavailable')),
  )

  await page.goto(`${VIEW_PATH}?Modality=CT&Patient%20Sex=M`)

  await expect(page.getByText('Values unavailable').first()).toBeVisible()
  // The filter after the failing one must still be applied.
  await expect(page.getByText(/M\s+\(3\)/)).toBeVisible()
  await expect(page.getByText('CT Thorax')).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

test('a failing project lookup is reported and the gallery still renders', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await page.route(/\/aii\/(projects|users\/[^/]+\/projects)$/, (r) =>
    r.fulfill(serverError('Projects unavailable')),
  )

  await page.goto(VIEW_PATH)

  await expect(page.getByText('Projects unavailable')).toBeVisible()
  await expect(page.getByText('CT Thorax')).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})
