import { test, expect } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import {
  confirmAction,
  delayRoute,
  dialog,
  isSeriesListRequest,
  nextPost,
  nextRequest,
  openGallery,
  selectDataset,
} from './fixtures/helpers'

test('selecting a dataset scopes the query to its identifiers', async ({ page }) => {
  await openGallery(page)

  const loadByName = nextRequest(page, /\/client\/dataset\?.*name=nsclc/, 'GET')
  const scopedSeries = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('"ids"'),
  )

  await selectDataset(page, 'nsclc (project)')

  await loadByName
  const body = (await scopedSeries).postDataJSON()
  const asText = JSON.stringify(body.query)
  expect(asText).toContain('1.2.3')
  expect(asText).toContain('4.5.6')
})

test('an empty dataset shows no series and says the dataset is empty', async ({ page }) => {
  const data = makeDefaultMockData()
  data.datasets.push({ ...data.datasets[0], name: 'empty-ds', identifiers: [] })
  await openGallery(page, data)

  const scopedSeries = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('"ids"'),
  )
  await selectDataset(page, 'empty-ds (project)')
  expect((await scopedSeries).postDataJSON().query.bool.must).toContainEqual({ ids: { values: [] } })

  await expect(page.getByText('This dataset contains no series yet')).toBeVisible()
  await expect(page.locator('.seriesCard')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /^Remove \d+ series/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: /^Download \d+ series/ })).toHaveCount(0)

  await page.getByRole('button', { name: 'Show all series' }).click()
  await expect(page.getByText('CT Thorax')).toBeVisible()
  await expect(page.getByLabel('Select Dataset').first()).toHaveValue('')
})

test('a search that matches nothing inside a dataset is not "dataset empty"', async ({ page }) => {
  await openGallery(page)
  await selectDataset(page, 'nsclc (project)')
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.route(/\/kaapana-backend\/dataset\/series$/, (route) =>
    (route.request().postData() ?? '').includes('nothing-matches-this')
      ? route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      : route.fallback(),
  )
  await page.getByLabel('Search').first().fill('nothing-matches-this')
  await page.getByRole('button', { name: 'Search', exact: true }).click()

  await expect(page.getByText('No series match the current search')).toBeVisible()
  await expect(page.getByText('This dataset contains no series yet')).toHaveCount(0)
})

test('Save as Dataset dialog posts the loaded series as a new dataset', async ({ page }) => {
  await openGallery(page)

  const createReq = nextPost(page, /\/client\/dataset$/)

  await page.locator('.mdi-plus').click()
  await expect(page.getByText('Save selection as dataset')).toBeVisible()
  await page.getByLabel('Name').first().fill('cohort-x')
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  const body = await createReq
  expect(body.name).toBe('cohort-x')
  expect(body.identifiers).toHaveLength(3)
  expect(body.access_level).toBe('private')
  await expect(page.getByText('Dataset created')).toBeVisible()
})

test('Add to Dataset dialog issues an ADD update for the chosen dataset', async ({ page }) => {
  await openGallery(page)

  const updateReq = nextRequest(page, /\/client\/dataset$/, 'PUT')

  await page.locator('.mdi-folder-plus-outline').click()
  const addTo = dialog(page, 'Add to Dataset')
  await expect(addTo).toBeVisible()
  await addTo.locator('.v-field').click()
  await page.getByRole('option', { name: 'nsclc (project)' }).click()
  await addTo.getByRole('button', { name: 'Save', exact: true }).click()

  const body = (await updateReq).postDataJSON()
  expect(body.action).toBe('ADD')
  expect(body.name).toBe('nsclc')
})

test('Edit Datasets dialog lists datasets and deletes one', async ({ page }) => {
  await openGallery(page)

  await page.locator('.mdi-folder-edit-outline').click()
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'my-private', exact: true })).toBeVisible()

  const deleteReq = nextRequest(page, /\/client\/dataset\?.*name=nsclc/, 'DELETE')
  await page.getByRole('button', { name: 'Delete dataset nsclc' }).click()
  await expect(page.getByText('Delete dataset “nsclc”?')).toBeVisible()
  await expect(page.getByText(/series it references stay in the project/)).toBeVisible()
  await confirmAction(page, 'Delete')

  await deleteReq
  await expect(page.getByText('Dataset deleted')).toBeVisible()
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toHaveCount(0)
})

// The backend addresses a dataset by name AND access level, defaulting to
// "project": a delete without the level 404s for a private dataset.
test('deleting a private dataset sends its access level', async ({ page }) => {
  await openGallery(page)
  await page.getByRole('button', { name: 'Manage datasets' }).click()

  const deleteReq = nextRequest(page, /\/client\/dataset\?/, 'DELETE')
  await page.getByRole('button', { name: /^Delete dataset my-private/ }).click()
  await confirmAction(page, 'Delete')

  const params = new URL((await deleteReq).url()).searchParams
  expect(params.get('name')).toBe('my-private')
  expect(params.get('access_level')).toBe('private')
  await expect(page.getByText('Dataset deleted')).toBeVisible()
})

test('Edit Datasets dialog shows a loading indicator while datasets load', async ({ page }) => {
  await openGallery(page)

  // Delay only the dialog's datasets fetch so the loading state is observable.
  await delayRoute(page, /\/kaapana-backend\/client\/datasets(\?.*)?$/, 3000)

  await page.locator('.mdi-folder-edit-outline').click()
  await expect(page.locator('.v-data-table-progress .v-progress-linear')).toBeVisible()
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toBeVisible()
})
