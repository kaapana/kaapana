import { test, expect, type Request } from '@playwright/test'
import { bootGallery, makeDefaultMockData, VIEW_PATH } from './fixtures/mock-backend'

// POST that fetches the series list (loadPatients), as opposed to the GET
// single-series metadata calls.
function isSeriesListRequest(req: Request): boolean {
  return req.method() === 'POST' && /\/dataset\/series$/.test(req.url())
}

test('free-text search puts the query string into the outgoing series query', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const seriesReq = page.waitForRequest(isSeriesListRequest)
  await page.getByLabel('Search').first().fill('Thorax')
  await page.getByRole('button', { name: 'Search', exact: true }).click()

  const body = (await seriesReq).postDataJSON()
  expect(JSON.stringify(body.query)).toContain('"query":"Thorax"')
})

test('a query-param filter is composed into a match clause and its values are fetched', async ({ page }) => {
  const data = makeDefaultMockData()
  // The series query that carries the Modality filter (mapping key from query_values).
  const filteredSeriesReq = page.waitForRequest(
    (req) =>
      isSeriesListRequest(req) &&
      (req.postData() ?? '').includes('00080060 Modality_keyword'),
  )
  const valuesReq = page.waitForRequest(
    (req) => req.method() === 'POST' && /\/dataset\/query_values\/Modality$/.test(req.url()),
  )

  await bootGallery(page, data, VIEW_PATH + '?Modality=CT')

  await valuesReq
  const body = (await filteredSeriesReq).postDataJSON()
  const asText = JSON.stringify(body.query)
  expect(asText).toContain('00080060 Modality_keyword')
  expect(asText).toContain('CT')
  await expect(page.getByText('CT Thorax')).toBeVisible()
})
