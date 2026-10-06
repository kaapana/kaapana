import { test, expect } from '@playwright/test'
import { cards, failRoute, openView } from './fixtures/helpers'
import { defaultMockData } from './fixtures/mock-backend'

test('an empty project explains where entities come from', async ({ page }) => {
  await openView(page, { entities: [], schemas: {} })
  const empty = page.getByTestId('empty')
  await expect(empty).toContainText('No entities in this project yet')
  await expect(empty).toContainText('once data is imported')
})

test('a failed load shows the error with details and a way to retry', async ({ page }) => {
  let fail = true
  await openView(page, defaultMockData(), {
    waitFor: 'none',
    routes: (target) =>
      target.route(
        (url) => url.pathname.endsWith('/entities/index/full'),
        (route) =>
          fail
            ? route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Database is starting up' }),
              })
            : route.fallback(),
      ),
  })

  const error = page.getByTestId('load-error')
  await expect(error).toContainText('Entities could not be loaded')
  await expect(error).toContainText('Database is starting up')

  await error.getByRole('button', { name: 'Details' }).click()
  const details = page.getByRole('dialog').filter({ hasText: 'Copy details' })
  await expect(details).toContainText('503')
  await details.getByRole('button', { name: 'Close' }).click()

  fail = false
  await error.getByRole('button', { name: 'Try again' }).click()
  await expect(cards(page)).toHaveCount(3)
})

test('a filter without matches offers to change or turn it off', async ({ page }) => {
  const where = encodeURIComponent(
    JSON.stringify({ type: 'filter', field: 'metadata.series.modality', op: 'eq', value: 'XA' }),
  )
  await openView(page, defaultMockData(), { query: `?q=${where}&qa=1`, waitFor: 'none' })
  const noMatch = page.getByTestId('no-match')
  await expect(noMatch).toContainText('No entities match the filter')
  await noMatch.getByRole('button', { name: 'Turn filter off' }).click()
  await expect(cards(page)).toHaveCount(3)
  await expect(page.getByLabel('Apply filter')).not.toBeChecked()
})

test('a failing page load of more entities is reported', async ({ page }) => {
  await openView(page, defaultMockData(), {
    waitFor: 'none',
    routes: (target) => failRoute(target, /\/entities\/records$/, 'Query timed out'),
  })
  await expect(
    page.locator('.vue-notification-wrapper').filter({ hasText: 'Entities not loaded' }),
  ).toBeVisible()
})
