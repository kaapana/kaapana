// Failure paths: a failed fetch must be reported once and leave the view usable.
import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, makeDefaultMockData, VIEW_PATH } from './fixtures/mock-backend'
import { collectPageErrors, failRoute } from './fixtures/helpers'

test('a ?dataset_name deep link reports a failing dataset list instead of "not found"', async ({
  page,
}) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  const pageErrors = collectPageErrors(page)

  await failRoute(page, /\/kaapana-backend\/client\/datasets(\?.*)?$/, 'Datasets unavailable')

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

  const pageErrors = collectPageErrors(page)

  await failRoute(page, /\/dataset\/query_values\/Modality$/, 'Values unavailable')

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

  const pageErrors = collectPageErrors(page)

  await failRoute(page, /\/aii\/(projects|users\/[^/]+\/projects)$/, 'Projects unavailable')

  await page.goto(VIEW_PATH)

  await expect(page.getByText('Projects unavailable')).toBeVisible()
  await expect(page.getByText('CT Thorax')).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})
