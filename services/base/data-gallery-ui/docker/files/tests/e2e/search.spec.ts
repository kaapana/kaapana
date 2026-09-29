import { test, expect } from '@playwright/test'
import { bootGallery, makeDefaultMockData, VIEW_PATH } from './fixtures/mock-backend'
import { isSeriesListRequest, nextRequest, openGallery } from './fixtures/helpers'

test('free-text search puts the query string into the outgoing series query', async ({ page }) => {
  await openGallery(page)

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
  const valuesReq = nextRequest(page, /\/dataset\/query_values\/Modality$/, 'POST')

  await bootGallery(page, data, VIEW_PATH + '?Modality=CT')

  await valuesReq
  const body = (await filteredSeriesReq).postDataJSON()
  const asText = JSON.stringify(body.query)
  expect(asText).toContain('00080060 Modality_keyword')
  expect(asText).toContain('CT')
  await expect(page.getByText('CT Thorax')).toBeVisible()
})
