import { test, expect, type Page } from '@playwright/test'
import { makeDefaultMockData, type MockData } from './fixtures/mock-backend'
import {
  countRequests,
  delayRoute,
  isSeriesListRequest,
  openGallery,
  serverError,
} from './fixtures/helpers'

const DASHBOARD = /\/kaapana-backend\/dataset\/dashboard$/

function withCharts(): MockData {
  const data = makeDefaultMockData()
  data.dashboard.histograms = {
    Modality: { items: { CT: 2, MR: 1 }, key: '00080060 Modality_keyword' },
  }
  return data
}

const charts = (page: Page) => page.locator('.apexcharts-canvas')

async function search(page: Page) {
  await page.getByRole('button', { name: 'Search', exact: true }).click()
}

test('the statistics are requested once at boot', async ({ page }) => {
  const requests = countRequests(page, DASHBOARD)
  await openGallery(page, withCharts())
  await expect(charts(page)).toHaveCount(1)
  await page.waitForTimeout(1_000)
  expect(requests()).toBe(1)
})

test('the charts stay while the statistics reload', async ({ page }) => {
  await openGallery(page, withCharts())
  await expect(charts(page)).toHaveCount(1)
  await delayRoute(page, DASHBOARD, 2_000)

  const reloaded = page.waitForResponse((r) => DASHBOARD.test(r.url()))
  await search(page)
  await expect(page.getByTestId('dashboard-progress')).toBeVisible()
  // Sampled across the reload: the chart never leaves the page.
  for (let i = 0; i < 8; i++) {
    expect(await charts(page).count()).toBeGreaterThanOrEqual(1)
    await page.waitForTimeout(200)
  }
  await reloaded
  await expect(page.getByTestId('dashboard-progress')).toBeHidden()
  await expect(charts(page)).toHaveCount(1)
})

test('clicking a bar adds its value to the search as a filter', async ({ page }) => {
  await openGallery(page, withCharts())
  await expect(charts(page)).toHaveCount(1)

  const filtered = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('Modality_keyword'),
  )
  await page.locator('.apexcharts-bar-area').first().click()
  await expect(page.getByText(/CT\s+\(2\)/)).toBeVisible()
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  expect(JSON.stringify((await filtered).postDataJSON().query)).toContain(
    '"00080060 Modality_keyword":"CT"',
  )
})

test('a failed reload clears the numbers of the previous one', async ({ page }) => {
  await openGallery(page, withCharts())
  const patients = page.locator('.text-h5').first()
  await expect(patients).toHaveText('1')

  await page.route(DASHBOARD, (r) => r.fulfill(serverError('Boom')))
  await search(page)
  await expect(page.getByTestId('dashboard-failure')).toBeVisible()
  await expect(patients).toHaveText('—')
  await expect(charts(page)).toHaveCount(0)
})
