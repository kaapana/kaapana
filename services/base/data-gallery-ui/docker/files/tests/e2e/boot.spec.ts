import { test, expect } from '@playwright/test'
import {
  bootGallery,
  installMockBackend,
  makeDefaultMockData,
  VIEW_PATH,
} from './fixtures/mock-backend'
import { collectPageErrors, failRoute, openGallery, toasts } from './fixtures/helpers'

// Every other spec seeds localStorage["settings"], so only this one sees a fresh
// profile — where the view's bare JSON.parse(undefined) at setup blanked the
// whole document.
test('renders on a fresh profile, with no shell-seeded settings', async ({ page }) => {
  const pageErrors = collectPageErrors(page)

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
  const pageErrors = collectPageErrors(page)

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
  await openGallery(page)

  // First card renders eagerly with its DICOM metadata (later cards are v-lazy).
  await expect(page.locator('.seriesCard').first()).toBeVisible()
  // Toolbar reflects the loaded series count (all loaded series are "of interest").
  await expect(page.getByText('3 selected')).toBeVisible()
})

test('series cards fill their grid column', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 1000 })
  await openGallery(page)
  const cards = page.locator('.seriesCard')
  await expect(cards).toHaveCount(3)

  const ratios = () =>
    cards.evaluateAll((els) =>
      els.map((card) => {
        const column = card.closest('.v-col')!
        return card.getBoundingClientRect().width / column.getBoundingClientRect().width
      }),
    )
  await expect.poll(async () => Math.min(...(await ratios()))).toBeGreaterThanOrEqual(0.9)
})

test('shows the "nothing yet" empty state when the project has no series', async ({ page }) => {
  const data = makeDefaultMockData()
  data.seriesUids = []
  data.aggregatedSeriesNum = 0
  await bootGallery(page, data)

  await expect(page.getByText('No imaging data in this project yet')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Go to Data Upload' })).toBeVisible()
  await expect(page.locator('.seriesCard')).toHaveCount(0)
})

test('a failed series count is reported once, as a failure', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  // Later route wins: fail the aggregated-count call the view issues on load.
  await failRoute(page, /\/dataset\/aggregatedSeriesNum$/, 'Boom')
  // Re-trigger a load by reloading with the failing route in place.
  await page.reload()

  await expect(page.getByText('Could not load the series')).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
  // The failed load must also clear the loading state — the skeleton loader
  // used to spin forever because the promise chain had no catch.
  await expect(page.locator('.v-skeleton-loader')).toHaveCount(0)
  await expect(page.getByText('Boom')).toHaveCount(0)
  await expect(toasts(page)).toHaveCount(0)
})
