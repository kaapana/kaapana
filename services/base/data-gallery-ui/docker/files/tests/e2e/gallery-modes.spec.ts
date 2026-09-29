import { test, expect } from '@playwright/test'
import { bootGallery, makeDefaultMockData } from './fixtures/mock-backend'
import { isSeriesListRequest, openGallery } from './fixtures/helpers'

test('structured mode requests structured series and renders grouped cards', async ({ page }) => {
  const data = makeDefaultMockData()
  data.settings.datasets.structured = true

  const structuredReq = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('"structured":true'),
  )
  await bootGallery(page, data)

  await structuredReq
  await expect(page.locator('.seriesCard').first()).toBeVisible()
  await expect(page.getByText('CT Thorax')).toBeVisible()
})

test('pagination appears when results exceed the page size and drives the page index', async ({ page }) => {
  const data = makeDefaultMockData()
  data.settings.datasets.itemsPerPagePagination = 2
  data.aggregatedSeriesNum = 5
  data.seriesUids = ['1.2.3', '4.5.6', '7.8.9', '10.11', '12.13']
  await openGallery(page, data)

  // ceil(5 / 2) = 3 pages -> pagination visible.
  const pagination = page.locator('.v-pagination')
  await expect(pagination).toBeVisible()

  const pageTwoReq = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('"pageIndex":2'),
  )
  await page.getByRole('button', { name: 'Go to page 2' }).click()
  await pageTwoReq
})
