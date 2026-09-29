import { test, expect, type Page } from '@playwright/test'
import {
  bootGallery,
  installMockBackend,
  makeDefaultMockData,
  seedShellState,
  VIEW_PATH,
} from './fixtures/mock-backend'
import {
  delayRoute,
  isSeriesListRequest,
  nextRequest,
  openGallery,
} from './fixtures/helpers'

test('free-text search puts the query string into the outgoing series query', async ({ page }) => {
  await openGallery(page)

  const seriesReq = page.waitForRequest(isSeriesListRequest)
  await page.getByLabel('Search').first().fill('Thorax')
  await page.getByRole('button', { name: 'Search', exact: true }).click()

  const body = (await seriesReq).postDataJSON()
  expect(JSON.stringify(body.query)).toContain('"query":"Thorax"')
})

// Located by its text: while loading, Vuetify hides the label from the accessible name.
const searchButton = (page: Page) => page.locator('button.v-btn').filter({ hasText: /^\s*Search\s*$/ })
const SERIES = /\/kaapana-backend\/dataset\/series$/

/** Read ONCE while the list loads: a retrying not.toHaveClass would wait for the load to end. */
async function spinsDuringLoad(page: Page) {
  const skeleton = page.locator('.v-skeleton-loader').first()
  await expect(skeleton).toBeVisible()
  const spinning = /v-btn--loading/.test((await searchButton(page).getAttribute('class')) ?? '')
  expect(await skeleton.isVisible(), 'the load ended before the read').toBe(true)
  return spinning
}

test('the initial load does not spin the Search button', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)
  await delayRoute(page, SERIES, 2_000)
  await page.goto(VIEW_PATH)

  expect(await spinsDuringLoad(page)).toBe(false)
})

test('a search the user starts spins the Search button until its results arrive', async ({ page }) => {
  await openGallery(page)
  await delayRoute(page, SERIES, 2_000)

  await searchButton(page).click()
  await expect(searchButton(page)).toHaveClass(/v-btn--loading/)
  await expect(page.getByText('CT Thorax')).toBeVisible()
  await expect(searchButton(page)).not.toHaveClass(/v-btn--loading/)
})

test('a query-param filter is composed into a match clause and its values are fetched', async ({ page }) => {
  const data = makeDefaultMockData()
  // The series query that carries the Modality filter (mapping key from query_values).
  const filteredSeriesReq = page.waitForRequest(
    (req) =>
      isSeriesListRequest(req) &&
      (req.postData() ?? '').includes('00080060 Modality_keyword'),
  )
  const valuesReq = nextRequest(page, /\/dataset\/query_values\/Modality$/, 'POST')

  await bootGallery(page, data, VIEW_PATH + '?Modality=CT')

  await valuesReq
  const body = (await filteredSeriesReq).postDataJSON()
  const asText = JSON.stringify(body.query)
  expect(asText).toContain('00080060 Modality_keyword')
  expect(asText).toContain('CT')
  await expect(page.getByText('CT Thorax')).toBeVisible()
})
