import { test, expect } from '@playwright/test'
import { bootGallery, makeDefaultMockData } from './fixtures/mock-backend'

test('deleting a tag chip on a series posts a tags2delete update', async ({ page }) => {
  const data = makeDefaultMockData()
  data.seriesData['1.2.3'].metadata.Tags = ['review']
  await bootGallery(page, data)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const card = page.locator('.seriesCard').first()
  await expect(card.getByText('review')).toBeVisible()

  const tagReq = page.waitForRequest(
    (req) => req.method() === 'POST' && /\/dataset\/tag$/.test(req.url()),
  )
  await card.locator('.v-chip__close').first().click()

  const body = (await tagReq).postDataJSON()
  const asText = JSON.stringify(body)
  expect(asText).toContain('tags2delete')
  expect(asText).toContain('review')
})
