import { test, expect, type Page } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import { nextPost, openGallery } from './fixtures/helpers'

const cards = (page: Page) => page.locator('.seriesCard')

test('clicking a card selects it, and Ctrl-clicking adds another', async ({ page }) => {
  await openGallery(page)
  await expect(page.getByText('3 selected')).toBeVisible()

  await cards(page).nth(0).click()
  await expect(page.getByText('1 selected of 3')).toBeVisible()
  await expect(cards(page).nth(0)).toHaveClass(/selected/)

  await page.keyboard.down('Control')
  await cards(page).nth(1).click()
  await page.keyboard.up('Control')
  await expect(page.getByText('2 selected of 3')).toBeVisible()
  await expect(cards(page).nth(1)).toHaveClass(/selected/)
})

/** The card boxes once the lazily rendered cards have stopped moving. */
async function settledBoxes(page: Page) {
  const read = () =>
    cards(page).evaluateAll((els) =>
      els.map((el) => {
        const r = el.getBoundingClientRect()
        return { x: r.x, y: r.y, width: r.width, height: r.height }
      }),
    )
  let previous = JSON.stringify(await read())
  await expect
    .poll(async () => {
      const current = JSON.stringify(await read())
      const stable = current === previous
      previous = current
      return stable
    })
    .toBe(true)
  return read()
}

test('dragging across cards selects them', async ({ page }) => {
  await openGallery(page)
  // Every card has its metadata and nothing is loading any more, so the cards
  // no longer move under the pointer.
  await expect(cards(page)).toHaveCount(3)
  for (const [index, text] of ['CT Thorax', 'MR Brain', 'CT Abdomen'].entries()) {
    await expect(cards(page).nth(index)).toContainText(text)
  }
  await page.waitForLoadState('networkidle')
  const [first, second] = await settledBoxes(page)

  // From inside the first card (away from its buttons) to inside the second.
  await page.mouse.move(first.x + first.width / 2, first.y + first.height - 10)
  await page.mouse.down()
  await page.mouse.move(second.x + second.width / 2, second.y + second.height - 10, { steps: 10 })
  await page.mouse.up()

  await expect(page.getByText('2 selected of 3')).toBeVisible()
  await expect(cards(page).nth(2)).not.toHaveClass(/selected/)
})

test('clicking a card with an active tag tags it, and clicking again untags it', async ({ page }) => {
  const data = makeDefaultMockData()
  data.settings.datasets.tagBar.tags = ['review']
  await openGallery(page, data)
  await page.locator('.v-chip-group .v-chip').filter({ hasText: 'review' }).click()

  const card = cards(page).nth(0)
  const tagged = nextPost(page, /\/dataset\/tag$/)
  await card.click()
  expect(await tagged).toEqual([
    { series_instance_uid: '1.2.3', tags: [], tags2add: ['review'], tags2delete: [] },
  ])
  await expect(card.locator('.v-chip').filter({ hasText: 'review' })).toBeVisible()

  const untagged = nextPost(page, /\/dataset\/tag$/)
  await card.click()
  expect(await untagged).toEqual([
    { series_instance_uid: '1.2.3', tags: ['review'], tags2add: [], tags2delete: ['review'] },
  ])
  await expect(card.locator('.v-chip').filter({ hasText: 'review' })).toHaveCount(0)
})
