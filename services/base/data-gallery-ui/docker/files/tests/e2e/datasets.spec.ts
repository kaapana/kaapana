import { test, expect } from '@playwright/test'
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

  const deleteReq = nextRequest(page, /\/client\/dataset\?.*name=/, 'DELETE')
  await page.locator('.mdi-delete').first().click()
  await expect(page.getByText('Delete dataset “my-private”?')).toBeVisible()
  await expect(page.getByText(/series it references stay in the project/)).toBeVisible()
  await confirmAction(page, 'Delete')

  await deleteReq
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
