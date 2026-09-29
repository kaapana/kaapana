import { test, expect, type Page } from '@playwright/test'
import { bootGallery, makeDefaultMockData, VIEW_PATH } from './fixtures/mock-backend'
import {
  confirmAction,
  countRequests,
  delayRoute,
  dialog,
  dismissWithEscape,
  isSeriesListRequest,
  nextPost,
  nextRequest,
  openGallery,
  selectDataset,
  serverError,
  toasts,
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

// Until the dataset has loaded the gallery shows the previous results, so Remove waits.
test('a selected dataset shows its progress, and Remove waits until it has loaded', async ({ page }) => {
  await openGallery(page)
  await delayRoute(page, /\/client\/dataset\?/, 2_000, 'GET')
  await selectDataset(page, 'nsclc (project)')
  const selectorProgress = page.locator('.v-autocomplete').first().locator('.v-progress-linear--active')

  await expect(page.getByText('CT Abdomen')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Loading the dataset…' })).toBeDisabled()
  await expect(selectorProgress).toBeVisible()

  await expect(page.getByRole('button', { name: 'Remove 2 series from “nsclc”' })).toBeEnabled()
  await expect(page.getByText('CT Abdomen')).toHaveCount(0)
  await expect(selectorProgress).toHaveCount(0)
})

test('removing some series from a dataset lowers the result count', async ({ page }) => {
  await openGallery(page)
  await selectDataset(page, 'nsclc (project)')
  await expect(page.getByText('MR Brain')).toBeVisible()
  await page.locator('.seriesCard').first().click()
  await expect(page.getByText('1 selected of 2')).toBeVisible()

  await page.getByRole('button', { name: 'Remove 1 series from “nsclc”' }).click()
  await confirmAction(page, 'Remove')
  await expect(page.locator('.seriesCard')).toHaveCount(1)
  await expect(page.getByText('1 selected', { exact: true })).toBeVisible()
})

/* ------------------------------------------------------------ deep links -- */

const selector = (page: Page) => page.locator('.v-autocomplete').first()

// A deep link sets the dataset and its filters together, then reports the
// dataset to the view. The view selecting that dataset must not start the
// search over, which would send a second, unfiltered search and drop the
// link's filters. The dataset load is slowed so that, if it does, the second
// search can be measured reliably.
test('a ?dataset_name deep link selects the dataset and keeps its filters', async ({ page }) => {
  // Boot once so the mock backend's routes exist; routes added later win.
  await openGallery(page)
  // A slow dataset load, as on a platform.
  await delayRoute(page, /\/client\/dataset\?/, 800, 'GET')
  const seriesRequests = countRequests(page, /\/dataset\/series$/, 'POST')
  const scopedAndFiltered = page.waitForRequest((req) => {
    const body = req.postData() ?? ''
    return isSeriesListRequest(req) && body.includes('"ids"') && body.includes('Modality_keyword')
  })
  await page.goto(`${VIEW_PATH}?dataset_name=nsclc&Modality=CT`)

  const query = JSON.stringify((await scopedAndFiltered).postDataJSON().query)
  expect(query).toContain('"ids":{"values":["1.2.3","4.5.6"]}')
  expect(query).toContain('"00080060 Modality_keyword":"CT"')
  await expect(page.getByText('CT Thorax')).toBeVisible()
  await expect(selector(page)).toContainText('nsclc (project)')
  await expect(page.getByText(/CT\s+\(2\)/)).toBeVisible()
  await expect(page.getByRole('button', { name: /^Remove \d+ series from “nsclc”/ })).toBeEnabled()

  await page.waitForTimeout(2_000)
  expect(seriesRequests()).toBe(1)
  await expect(page.getByText(/CT\s+\(2\)/)).toBeVisible()
})

test('a deep link with access_level=private selects the private dataset', async ({ page }) => {
  const scoped = page.waitForRequest(
    (req) => isSeriesListRequest(req) && (req.postData() ?? '').includes('"ids"'),
  )
  await bootGallery(
    page,
    makeDefaultMockData(),
    `${VIEW_PATH}?dataset_name=my-private&access_level=private`,
  )

  expect(JSON.stringify((await scoped).postDataJSON().query)).toContain('["7.8.9"]')
  await expect(selector(page)).toContainText('my-private (private)')
  await expect(page.getByText('CT Abdomen')).toBeVisible()
})

test('a name-only deep link prefers the project dataset, then the private one', async ({ page }) => {
  const data = makeDefaultMockData()
  data.datasets.push({ ...data.datasets[1], name: 'nsclc' })
  await bootGallery(page, data, `${VIEW_PATH}?dataset_name=nsclc`)
  await expect(selector(page)).toContainText('nsclc (project)')

  await page.goto(`${VIEW_PATH}?dataset_name=my-private`)
  await expect(selector(page)).toContainText('my-private (private)')
})

// Changing a gallery setting in the shell remounts the view. The remounted view
// must not apply the original deep link again over what the user changed since.
test('a deep link is applied once, not again when the view remounts', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData(), `${VIEW_PATH}?dataset_name=nsclc&Modality=CT`)
  await expect(page.getByText(/CT\s+\(2\)/)).toBeVisible()
  await expect(selector(page)).toContainText('nsclc (project)')
  await expect(page).toHaveURL(new RegExp(`${VIEW_PATH}$`))
  await page.getByRole('button', { name: 'Remove filter' }).click()
  await expect(page.getByText(/CT\s+\(2\)/)).toHaveCount(0)

  // Replay the shell's settings write. The browser fires "storage" only in other
  // documents, so the event is dispatched by hand.
  await page.evaluate(() => {
    const oldValue = localStorage.getItem('settings')
    const settings = JSON.parse(oldValue ?? '{}')
    settings.datasets.cols = 4
    const newValue = JSON.stringify(settings)
    localStorage.setItem('settings', newValue)
    window.dispatchEvent(new StorageEvent('storage', { key: 'settings', oldValue, newValue }))
  })

  await expect(page.getByText('CT Abdomen')).toBeVisible()
  await expect(selector(page)).not.toContainText('nsclc')
  await expect(page.getByText(/CT\s+\(2\)/)).toHaveCount(0)
})

test('the copied query link names the dataset with its access level', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await openGallery(page)
  await selectDataset(page, 'my-private (private)')
  await expect(page.getByText('CT Abdomen')).toBeVisible()

  await page.getByRole('button', { name: 'Copy query URL to clipboard' }).click()
  await expect(toasts(page).filter({ hasText: 'Copied' })).toBeVisible()
  const link = new URL(await page.evaluate(() => navigator.clipboard.readText()))
  expect(link.searchParams.get('dataset_name')).toBe('my-private')
  expect(link.searchParams.get('access_level')).toBe('private')
})

test('deleting the selected dataset clears the selection', async ({ page }) => {
  await openGallery(page)
  await selectDataset(page, 'nsclc (project)')
  await expect(page.getByText('MR Brain')).toBeVisible()

  await page.getByRole('button', { name: 'Manage datasets' }).click()
  await page.getByRole('button', { name: 'Delete dataset nsclc (project)' }).click()
  await confirmAction(page, 'Delete')
  await expect(page.getByText('Dataset deleted')).toBeVisible()
  await dismissWithEscape(page, dialog(page, 'Search datasets'))

  await expect(selector(page)).not.toContainText('nsclc')
  await expect(page.getByText('CT Abdomen')).toBeVisible()
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
  await page.getByRole('button', { name: 'Delete dataset nsclc (project)' }).click()
  const confirmation = dialog(page, 'Delete dataset?')
  await expect(confirmation).toContainText('“nsclc” (project)')
  await expect(confirmation).toContainText('series it references stay in the project')
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

/* ---------------------------------------------------------------- saving -- */

// Enter on a Vuetify button fires it even while it shows its loader, so a
// running save should also disable its button and its handler should ignore a second call.

const DATASET = /\/kaapana-backend\/client\/dataset(\?.*)?$/

test('Enter in the name saves once, shows progress, and cannot be dismissed meanwhile', async ({
  page,
}) => {
  await openGallery(page)
  await delayRoute(page, DATASET, 1_500, 'POST')
  const creates = countRequests(page, DATASET, 'POST')

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  const saveDialog = dialog(page, 'Save selection as dataset')
  const name = page.getByLabel('Name').first()
  await name.fill('cohort-x')
  // Located by place: while loading, the label is hidden from the accessible name.
  const save = saveDialog.locator('.v-card-actions .v-btn').last()
  await expect(save).toHaveText('Save')
  await name.press('Enter')

  await expect(save).toHaveClass(/v-btn--loading/)
  await expect(save).toBeDisabled()
  // Whatever holds focus now, Enter must not submit again.
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')
  await page.keyboard.press('Escape')
  await expect(saveDialog).toBeVisible()
  await expect(dialog(page, 'Discard this dataset?')).toHaveCount(0)

  await expect(toasts(page).filter({ hasText: 'Dataset created' })).toBeVisible()
  await expect(saveDialog).toHaveCount(0)
  expect(creates()).toBe(1)
})

test('adding to a dataset runs once, shows progress, and cannot be dismissed meanwhile', async ({
  page,
}) => {
  await openGallery(page)
  await delayRoute(page, DATASET, 1_500, 'PUT')
  const updates = countRequests(page, DATASET, 'PUT')

  await page.getByRole('button', { name: /^Add \d+ series to a dataset/ }).click()
  const addTo = dialog(page, 'Add to dataset')
  await addTo.locator('.v-field').click()
  await page.getByRole('option', { name: 'nsclc (project)' }).click()
  const save = addTo.locator('.v-card-actions .v-btn').last()
  await expect(save).toHaveText('Save')
  await save.click()

  await expect(save).toHaveClass(/v-btn--loading/)
  await expect(save).toBeDisabled()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')
  await page.keyboard.press('Escape')
  await expect(addTo).toBeVisible()

  await expect(toasts(page).filter({ hasText: 'Dataset updated' })).toBeVisible()
  await expect(addTo).toHaveCount(0)
  expect(updates()).toBe(1)
})

/* --------------------------------------------------------- dataset lists -- */

// "Empty states": a list that is loading, empty, filtered to nothing or failed
// should say which.

const DATASET_LIST = /\/kaapana-backend\/client\/datasets(\?.*)?$/
const SELECTOR_LIST = /\/kaapana-backend\/client\/datasets\?skip_identifiers=true$/
const NONE_YET = /No datasets have been created in this project yet/

test('Edit Datasets dialog shows a loading indicator while datasets load', async ({ page }) => {
  await openGallery(page)

  // Delay only the dialog's datasets fetch so the loading state is observable.
  await delayRoute(page, DATASET_LIST, 3000)

  await page.locator('.mdi-folder-edit-outline').click()
  await expect(page.locator('.v-data-table-progress .v-progress-linear')).toBeVisible()
  await expect(page.getByText('Loading datasets…')).toBeVisible()
  await expect(page.getByText(NONE_YET)).toHaveCount(0)
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toBeVisible()
})

test('Manage datasets tells a failed load apart from an empty list, and retries', async ({ page }) => {
  await openGallery(page)
  let failing = true
  await page.route(DATASET_LIST, (r) => (failing ? r.fulfill(serverError('Boom')) : r.fallback()))

  await page.getByRole('button', { name: 'Manage datasets' }).click()
  const manage = dialog(page, 'Search datasets')
  await expect(manage).toContainText('Could not load the datasets')
  await expect(manage.getByText(NONE_YET)).toHaveCount(0)

  failing = false
  await manage.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByRole('cell', { name: 'nsclc', exact: true })).toBeVisible()
})

test('the dataset selector tells a failed load apart from an empty list, and retries', async ({ page }) => {
  let failing = true
  await bootGallery(page, makeDefaultMockData())
  await page.route(SELECTOR_LIST, (r) => (failing ? r.fulfill(serverError('Boom')) : r.fallback()))
  await page.reload()
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.getByLabel('Select Dataset').first().click()
  await expect(page.getByText('The datasets could not be loaded. Reopen this list to try again.')).toBeVisible()
  await expect(page.getByText('No datasets in this project yet')).toHaveCount(0)

  failing = false
  await page.keyboard.press('Escape')
  await page.getByLabel('Select Dataset').first().click()
  await expect(page.getByRole('option', { name: 'nsclc (project)' })).toBeVisible()
})
