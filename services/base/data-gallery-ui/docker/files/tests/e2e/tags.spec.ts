import { test, expect } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import { nextPost, openGallery } from './fixtures/helpers'

test('deleting a tag chip on a series posts a tags2delete update', async ({ page }) => {
  const data = makeDefaultMockData()
  data.seriesData['1.2.3'].metadata.Tags = ['review']
  await openGallery(page, data)

  const card = page.locator('.seriesCard').first()
  await expect(card.getByText('review')).toBeVisible()

  const tagReq = nextPost(page, /\/dataset\/tag$/)
  await card.locator('.v-chip__close').first().click()

  const asText = JSON.stringify(await tagReq)
  expect(asText).toContain('tags2delete')
  expect(asText).toContain('review')
})
