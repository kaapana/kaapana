import { test, expect } from '@playwright/test'
import {
  bootGallery,
  installMockBackend,
  makeDefaultMockData,
  VIEW_PATH,
} from './fixtures/mock-backend'

// Every other spec seeds localStorage["settings"], so only this one sees a fresh
// profile — where the view's bare JSON.parse(undefined) at setup blanked the
// whole document.
test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))

  await installMockBackend(page, makeDefaultMockData())
  await page.goto(VIEW_PATH)

  await expect(page.getByText('CT Thorax')).toBeVisible()
  await expect(page.locator('.seriesCard').first()).toBeVisible()
  expect(pageErrors).toEqual([])
  // The unseeded boot must write the defaults back — that is what keeps the tag
  // bar's read-modify-write watchers off the throwing path.
  await expect
    .poll(async () => page.evaluate(() => JSON.parse(localStorage['settings'] ?? 'null')))
    .toMatchObject({ datasets: { props: expect.any(Array) } })
})

// The tag bar re-reads localStorage["settings"] to persist its controls —
// reachable only by interacting, so the boot test above does not cover it.
test('the tag bar persists its settings on a fresh profile', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))

  await installMockBackend(page, makeDefaultMockData())
  await page.goto(VIEW_PATH)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.getByLabel('Multiple Tags').first().click()

  await expect
    .poll(async () => page.evaluate(() => JSON.parse(localStorage['settings'] ?? 'null')))
    .toMatchObject({ datasets: { tagBar: { multiple: true } } })
  expect(pageErrors).toEqual([])
})

test('renders the series gallery from typical data', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())

  // First card renders eagerly with its DICOM metadata (later cards are v-lazy).
  await expect(page.getByText('CT Thorax')).toBeVisible()
  await expect(page.locator('.seriesCard').first()).toBeVisible()
  // Toolbar reflects the loaded series count (all loaded series are "of interest").
  await expect(page.getByText('3 selected')).toBeVisible()
})

test('shows the empty-state message when no series match', async ({ page }) => {
  const data = makeDefaultMockData()
  data.seriesUids = []
  data.aggregatedSeriesNum = 0
  await bootGallery(page, data)

  await expect(page.getByText('No data found.')).toBeVisible()
  await expect(page.locator('.seriesCard')).toHaveCount(0)
})

test('surfaces a backend error as a notification', async ({ page }) => {
  const data = makeDefaultMockData()
  await bootGallery(page, data)
  // Later route wins: fail the aggregated-count call the view issues on load.
  await page.route(/\/dataset\/aggregatedSeriesNum$/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Boom' }),
    }),
  )
  // Re-trigger a load by reloading with the failing route in place.
  await page.reload()

  await expect(page.getByText('Boom')).toBeVisible()
  // The failed load must also clear the loading state — the skeleton loader
  // used to spin forever because the promise chain had no catch.
  await expect(page.locator('.v-skeleton-loader')).toHaveCount(0)
})
