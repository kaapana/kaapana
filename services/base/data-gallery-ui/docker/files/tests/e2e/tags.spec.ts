import { test, expect } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import { nextPost, openGallery } from './fixtures/helpers'

// "Meaning must not depend on color perception alone."
test('a selected tag chip is marked and announced, not only coloured', async ({ page }) => {
  const data = makeDefaultMockData()
  data.settings.datasets.tagBar.tags = ['review', 'favorite']
  await openGallery(page, data)

  const chip = page.locator('.v-chip-group .v-chip').filter({ hasText: 'review' })
  const marker = chip.locator('.v-chip__filter .v-icon')
  const toggle = (pressed: boolean) =>
    page.getByRole('button', { name: 'review', exact: true, pressed })
  await expect(toggle(false)).toBeVisible()
  await expect(marker).toBeHidden()

  await chip.click()
  await expect(toggle(true)).toBeVisible()
  await expect(marker).toBeVisible()

  await chip.click()
  await expect(toggle(false)).toBeVisible()
  await expect(marker).toBeHidden()
})

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
  await expect(card.getByText('review')).toHaveCount(0)
})
