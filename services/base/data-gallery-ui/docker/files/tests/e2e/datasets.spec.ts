import { test, expect, type Request } from '@playwright/test'
import { bootGallery, makeDefaultMockData } from './fixtures/mock-backend'

function isSeriesListRequest(req: Request): boolean {
  return req.method() === 'POST' && /\/dataset\/series$/.test(req.url())
}

test('selecting a dataset scopes the query to its identifiers', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const loadByName = page.waitForRequest(
    (req) => req.method() === 'GET' && /\/client\/dataset\?.*name=nsclc/.test(req.url()),
  )
  const scopedSeries = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('"ids"'),
  )

  await page.getByLabel('Select Dataset').first().click()
  await page.getByRole('option', { name: 'nsclc (project)' }).click()

  await loadByName
  const body = (await scopedSeries).postDataJSON()
  const asText = JSON.stringify(body.query)
  expect(asText).toContain('1.2.3')
  expect(asText).toContain('4.5.6')
})

test('Save as Dataset dialog posts the loaded series as a new dataset', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const createReq = page.waitForRequest(
    (req) => req.method() === 'POST' && /\/client\/dataset$/.test(req.url()),
  )

  await page.locator('.mdi-plus').click()
  await expect(page.getByText('Save selection as dataset')).toBeVisible()
  await page.getByLabel('Name').first().fill('cohort-x')
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  const body = (await createReq).postDataJSON()
  expect(body.name).toBe('cohort-x')
  expect(body.identifiers).toHaveLength(3)
  expect(body.access_level).toBe('private')
  await expect(page.getByText('Dataset created')).toBeVisible()
})

test('Add to Dataset dialog issues an ADD update for the chosen dataset', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const updateReq = page.waitForRequest(
    (req) => req.method() === 'PUT' && /\/client\/dataset$/.test(req.url()),
  )

  await page.locator('.mdi-folder-plus-outline').click()
  const dialog = page.getByRole('dialog').filter({ hasText: 'Add to Dataset' })
  await expect(dialog).toBeVisible()
  await dialog.locator('.v-field').click()
  await page.getByRole('option', { name: 'nsclc (project)' }).click()
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()

  const body = (await updateReq).postDataJSON()
  expect(body.action).toBe('ADD')
  expect(body.name).toBe('nsclc')
})

test('Edit Datasets dialog lists datasets and deletes one', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.locator('.mdi-folder-edit-outline').click()
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'my-private', exact: true })).toBeVisible()

  const deleteReq = page.waitForRequest(
    (req) => req.method() === 'DELETE' && /\/client\/dataset\?.*name=/.test(req.url()),
  )
  await page.locator('.mdi-delete').first().click()
  // The confirmation names what is affected and what follows, rather than
  // asking "are you sure?" about an unnamed thing.
  await expect(page.getByText('Delete dataset “my-private”?')).toBeVisible()
  await expect(page.getByText(/series it references stay in the project/)).toBeVisible()
  await page.getByRole('button', { name: 'Delete', exact: true }).click()

  await deleteReq
  await expect(page.getByText('Dataset deleted')).toBeVisible()
})

test('Edit Datasets dialog shows a loading indicator while datasets load', async ({ page }) => {
  const data = makeDefaultMockData()
  await bootGallery(page, data)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // Delay only the dialog's datasets fetch so the loading state is observable.
  await page.route(/\/kaapana-backend\/client\/datasets(\?.*)?$/, async (r) => {
    await new Promise((res) => setTimeout(res, 3000))
    return r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data.datasets),
    })
  })

  await page.locator('.mdi-folder-edit-outline').click()
  await expect(page.locator('.v-data-table-progress .v-progress-linear')).toBeVisible()
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toBeVisible()
})
