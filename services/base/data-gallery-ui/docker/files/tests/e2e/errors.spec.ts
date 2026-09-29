import { test, expect, type Page } from '@playwright/test'
import {
  installMockBackend,
  makeDefaultMockData,
  seedShellState,
  VIEW_PATH,
} from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  dialog,
  failRoute,
  openFailureDetails,
  openGallery,
  selectDataset,
  serverError,
  toasts,
} from './fixtures/helpers'

const SERIES = /\/kaapana-backend\/dataset\/series$/

/** Waits long enough for a late second report to show up. */
async function settle(page: Page) {
  await page.waitForTimeout(700)
}

test.describe('reported inline', () => {
  test('a failed first load is the error empty state with Retry and Details, not a toast', async ({
    page,
  }) => {
    const pageErrors = collectPageErrors(page)
    await installMockBackend(page)
    let failing = true
    await page.route(SERIES, (r) => (failing ? r.fulfill(serverError('Boom')) : r.fallback()))
    await page.goto(VIEW_PATH)

    const empty = page.getByTestId('gallery-empty-state')
    await expect(empty).toContainText('Could not load the series')
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
    await expect(page.getByText('Boom')).toHaveCount(0)
    await empty.getByRole('button', { name: 'Details' }).click()
    await expect(dialog(page).getByText('Boom')).toBeVisible()
    await dialog(page).getByRole('button', { name: 'Close' }).click()

    failing = false
    await empty.getByRole('button', { name: 'Try again' }).click()
    await expect(page.getByText('CT Thorax')).toBeVisible()
    expect(pageErrors).toEqual([])
  })

  test('a failed search after a good load keeps the results, says they are stale, and never toasts', async ({
    page,
  }) => {
    await openGallery(page)
    let failing = true
    await page.route(SERIES, (r) => (failing ? r.fulfill(serverError('Boom')) : r.fallback()))
    await page.getByLabel('Search').first().fill('Thorax')
    await page.getByRole('button', { name: 'Search', exact: true }).click()

    const stale = page.getByTestId('stale-results-alert')
    await expect(stale).toContainText('Could not load the results of this search')
    await expect(page.getByText('CT Thorax')).toBeVisible()
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
    await expect(stale).toHaveCount(1)

    await stale.getByRole('button', { name: 'Details' }).click()
    await expect(dialog(page).getByText('Boom')).toBeVisible()
    await dialog(page).getByRole('button', { name: 'Close' }).click()

    failing = false
    await stale.getByRole('button', { name: 'Try again' }).click()
    await expect(stale).toHaveCount(0)
    await expect(page.getByText('CT Thorax')).toBeVisible()
  })

  test('failed searchable fields are reported in the search row, and the search is retried', async ({
    page,
  }) => {
    await openGallery(page)
    let failing = true
    await page.route(/\/dataset\/search_fields$/, (r) =>
      failing ? r.fulfill(serverError('OpenSearch down')) : r.fallback(),
    )
    await page.getByLabel('Search').first().fill('Thorax')
    const filtersOnly = page.waitForRequest((r) => SERIES.test(r.url()) && r.method() === 'POST')
    await page.getByRole('button', { name: 'Search', exact: true }).click()

    expect((await filtersOnly).postData()).not.toContain('Thorax')
    const alert = page.getByTestId('search-alert')
    await expect(alert).toContainText('The free text was not applied')
    await expect(alert).toContainText('match the filters only')
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
    await alert.getByRole('button', { name: 'Details' }).click()
    await expect(dialog(page).getByText('OpenSearch down')).toBeVisible()
    await dialog(page).getByRole('button', { name: 'Close' }).click()

    failing = false
    const searched = page.waitForRequest(
      (r) => SERIES.test(r.url()) && (r.postData() ?? '').includes('"query":"Thorax"'),
    )
    await alert.getByRole('button', { name: 'Try again' }).click()
    await searched
    await expect(alert).toHaveCount(0)
  })

  // Free text needs the list of searchable fields. If that list fails to load,
  // the search still runs with the filters only and one inline
  // message says the free text was not applied, instead of a silent fallback.
  test('a free-text link whose searchable fields fail searches with the filters only, and says so', async ({
    page,
  }) => {
    await installMockBackend(page)
    await failRoute(page, /\/dataset\/search_fields$/, 'OpenSearch down')
    const statistics = page.waitForRequest(/\/dataset\/dashboard$/)
    await page.goto(`${VIEW_PATH}?query_string=Thorax`)

    await expect(page.getByText('CT Thorax')).toBeVisible()
    await expect(page.locator('.v-skeleton-loader')).toHaveCount(0)
    await statistics
    const alert = page.getByTestId('search-alert')
    await expect(alert).toContainText('The free text was not applied')
    await settle(page)
    await expect(alert).toHaveCount(1)
    await expect(toasts(page)).toHaveCount(0)
  })

  test('failed filter fields are reported in the search row', async ({ page }) => {
    await installMockBackend(page)
    await failRoute(page, /\/dataset\/field_names$/, 'mapping unavailable')
    await page.goto(VIEW_PATH)
    await expect(page.getByText('CT Thorax')).toBeVisible()

    await expect(page.getByTestId('search-alert')).toContainText('The fields to filter by could not be loaded')
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
  })

  test('failed filter values are reported in the search row', async ({ page }) => {
    await openGallery(page)
    await failRoute(page, /\/dataset\/query_values\/Modality$/, 'Values unavailable')

    await page.getByRole('button', { name: 'Add filter' }).click()
    await page.getByLabel('Field').first().click()
    await page.getByRole('option', { name: 'Modality', exact: true }).click()

    await expect(page.getByTestId('search-alert')).toContainText('The values of “Modality” could not be loaded')
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
  })

  test('failed statistics are reported in the dashboard only', async ({ page }) => {
    await installMockBackend(page)
    await failRoute(page, /\/dataset\/dashboard$/, 'Boom')
    await page.goto(VIEW_PATH)
    await expect(page.getByText('CT Thorax')).toBeVisible()

    await expect(page.getByText('The statistics for the current selection could not be loaded.')).toHaveCount(1)
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
  })

  test('a series whose metadata fails says so on its card, without a toast', async ({ page }) => {
    await installMockBackend(page)
    await failRoute(page, /\/dataset\/series\/1\.2\.3$/, 'Boom')
    await page.goto(VIEW_PATH)

    const card = page.locator('.seriesCard').first()
    await expect(card).toContainText('Metadata unavailable')
    await expect(card.locator('.v-progress-circular')).toHaveCount(0)
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
  })

  test('failed dataset lists are reported in their lists only', async ({ page }) => {
    await installMockBackend(page)
    await failRoute(page, /\/kaapana-backend\/client\/datasets(\?.*)?$/, 'Datasets unavailable')
    await page.goto(VIEW_PATH)
    await expect(page.getByText('CT Thorax')).toBeVisible()

    await page.getByLabel('Select Dataset').first().click()
    await expect(page.getByText('The datasets could not be loaded.', { exact: false })).toBeVisible()
    await page.keyboard.press('Escape')
    await page.getByRole('button', { name: 'Manage datasets' }).click()
    await expect(dialog(page, 'Search datasets')).toContainText('Could not load the datasets')
    await settle(page)
    await expect(toasts(page)).toHaveCount(0)
  })
})

test.describe('reported once as a notification', () => {
  test('a failing project lookup is one notification, and the gallery still renders', async ({ page }) => {
    const pageErrors = collectPageErrors(page)
    await installMockBackend(page)
    await failRoute(page, /\/aii\/(projects|users\/[^/]+\/projects)$/, 'Projects unavailable')
    await page.goto(`${VIEW_PATH}?project_name=admin`)

    await expect(page.getByText('CT Thorax')).toBeVisible()
    const details = await openFailureDetails(page, 'Project unavailable')
    await expect(details.getByText('Projects unavailable')).toBeVisible()
    await details.getByRole('button', { name: 'Close' }).click()
    await expect(toasts(page)).toHaveCount(0)
    expect(pageErrors).toEqual([])
  })

  test('a ?dataset_name link whose dataset list fails says so once, and searches unscoped', async ({
    page,
  }) => {
    const pageErrors = collectPageErrors(page)
    const data = makeDefaultMockData()
    await installMockBackend(page, data)
    await seedShellState(page, data)
    await failRoute(page, /\/kaapana-backend\/client\/datasets(\?.*)?$/, 'Datasets unavailable')
    await page.goto(`${VIEW_PATH}?dataset_name=nsclc`)

    await expect(page.getByText('CT Abdomen')).toBeVisible()
    await expect(toasts(page)).toHaveCount(1)
    await expect(toasts(page)).toContainText('Dataset link not applied')
    await expect(page.getByText('Datasets unavailable')).toHaveCount(0)
    expect(pageErrors).toEqual([])
  })

  test('a failing values lookup skips only its own deep-link filter, once', async ({ page }) => {
    const pageErrors = collectPageErrors(page)
    const data = makeDefaultMockData()
    await installMockBackend(page, data)
    await seedShellState(page, data)
    await failRoute(page, /\/dataset\/query_values\/Modality$/, 'Values unavailable')
    await page.goto(`${VIEW_PATH}?Modality=CT&Patient%20Sex=M`)

    await expect(page.getByText(/M\s+\(3\)/)).toBeVisible()
    await expect(page.getByText('CT Thorax')).toBeVisible()
    await expect(toasts(page)).toHaveCount(1)
    await expect(toasts(page)).toContainText('The filter “Modality” from the link could not be applied.')
    expect(pageErrors).toEqual([])
  })

  test('a dataset that cannot be loaded on selection is one notification; the selection goes back', async ({
    page,
  }) => {
    await openGallery(page)
    await failRoute(page, /\/kaapana-backend\/client\/dataset\?/, 'Boom', 500, 'GET')
    await selectDataset(page, 'nsclc (project)')

    await expect(toasts(page).filter({ hasText: 'Dataset not loaded' })).toHaveCount(1)
    await expect(page.locator('.v-autocomplete').first()).not.toContainText('nsclc')
    await expect(page.getByText('CT Abdomen')).toBeVisible()
    await expect(page.getByRole('button', { name: /select a dataset first/i })).toBeDisabled()
  })

  test('a dataset that cannot be reloaded after a removal is one notification', async ({ page }) => {
    await openGallery(page)
    await selectDataset(page, 'nsclc (project)')
    await expect(page.getByText('MR Brain')).toBeVisible()
    await failRoute(page, /\/kaapana-backend\/client\/dataset\?/, 'Boom', 500, 'GET')

    await page.getByRole('button', { name: /^Remove \d+ series from/ }).click()
    await confirmAction(page, 'Remove')

    await expect(toasts(page).filter({ hasText: 'Dataset updated' })).toBeVisible()
    await expect(toasts(page).filter({ hasText: 'Dataset not reloaded' })).toHaveCount(1)
    await settle(page)
    await expect(toasts(page).filter({ hasText: 'Dataset not reloaded' })).toHaveCount(1)
  })

  test('failed tag suggestions are one notification', async ({ page }) => {
    const data = makeDefaultMockData()
    await installMockBackend(page, data)
    await seedShellState(page, data)
    await failRoute(page, /\/dataset\/query_values\/Tags$/, 'Boom')
    await page.goto(VIEW_PATH)
    await expect(page.getByText('CT Thorax')).toBeVisible()

    await expect(toasts(page)).toHaveCount(1)
    await expect(toasts(page)).toContainText('Tag suggestions not loaded')
  })
})
