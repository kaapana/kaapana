import { test, expect, type Page } from '@playwright/test'
import { makeDefaultMockData, viewPathFor } from './fixtures/mock-backend'
import { delayRoute, dialog, openGallery, serverError, toasts } from './fixtures/helpers'

test('opening a series detail shows the OHIF viewer and its metadata table', async ({ page }) => {
  await openGallery(page)

  await page.locator('.seriesCard').first().locator('.mdi-eye').click()

  const viewer = page.locator('iframe[src*="ohif/viewer"]')
  await expect(viewer).toHaveAttribute('src', /study-1\.2\.3/)
  await expect(viewer).toHaveAttribute('src', /initialSeriesInstanceUID=1\.2\.3/)
  await expect(page.getByText('Metadata')).toBeVisible()
})

// OHIF derives its DICOMweb scope from the document URL, so an unprefixed viewer
// URL would load ANOTHER project's study. Boots a deliberately non-default
// project so a hardcoded or defaulted prefix fails too.
test('the OHIF viewer is embedded under the document project prefix', async ({ page }) => {
  const data = makeDefaultMockData()
  const project = data.projects[1]
  await openGallery(page, data, viewPathFor(project))

  await page.locator('.seriesCard').first().locator('.mdi-eye').click()

  const viewer = page.locator('iframe[src*="ohif/viewer"]')
  await expect(viewer).toHaveAttribute(
    'src',
    new RegExp(`^/project/${project.short_id}/ohif/viewer\\?`),
  )
})

/* ------------------------------------------------------------- metadata -- */

const METADATA = (uid: string) => new RegExp(`/dataset/series/${uid.replace(/\./g, '\\.')}$`)
const pane = (page: Page) => page.getByTestId('series-detail')
const openDetails = (page: Page, index: number) =>
  page.locator('.seriesCard').nth(index).getByRole('button', { name: 'Show series details' }).click()

test('a failed metadata load is one inline message with Retry and Details, not a toast', async ({
  page,
}) => {
  await openGallery(page)
  let failing = true
  await page.route(METADATA('1.2.3'), (r) => (failing ? r.fulfill(serverError('Boom')) : r.fallback()))
  await openDetails(page, 0)

  const alert = pane(page).getByTestId('metadata-alert')
  await expect(alert).toContainText('The metadata of this series could not be loaded.')
  await page.waitForTimeout(700)
  await expect(toasts(page)).toHaveCount(0)
  await expect(pane(page).getByText('No metadata was returned')).toHaveCount(0)
  await alert.getByRole('button', { name: 'Details' }).click()
  await expect(dialog(page).getByText('Boom')).toBeVisible()
  await dialog(page).getByRole('button', { name: 'Close' }).click()

  failing = false
  await alert.getByRole('button', { name: 'Try again' }).click()
  await expect(pane(page).getByRole('cell', { name: 'CT Thorax' })).toBeVisible()
  await expect(alert).toHaveCount(0)
})

test('a series whose metadata names no study says so, rather than loading the viewer', async ({
  page,
}) => {
  const data = makeDefaultMockData()
  delete data.seriesData['1.2.3'].metadata['Study Instance UID']
  await openGallery(page, data)
  await openDetails(page, 0)

  await expect(pane(page).getByRole('cell', { name: 'CT Thorax' })).toBeVisible()
  await expect(pane(page).getByText('No study to show')).toBeVisible()
  await expect(pane(page).getByText('Loading the viewer…')).toHaveCount(0)
  await expect(pane(page).locator('iframe')).toHaveCount(0)
})

test('switching series quickly shows the series picked last, not the slower answer', async ({
  page,
}) => {
  await openGallery(page)
  await delayRoute(page, METADATA('1.2.3'), 1_500)
  await openDetails(page, 0)
  await openDetails(page, 1)

  const title = pane(page).locator('.v-card-title').first()
  await expect(title).toContainText('MR Brain')
  // The slow answer for the first series arrives now and must be dropped.
  await page.waitForTimeout(2_000)
  await expect(title).toContainText('MR Brain')
  await expect(pane(page).getByRole('cell', { name: 'MR Brain' })).toBeVisible()
  await expect(pane(page).getByRole('cell', { name: 'CT Thorax' })).toHaveCount(0)
})

// The detail pane is narrow; fixed cols="1" title-bar columns (~31px) squeezed
// the 48px icon buttons into ovals. Guards the cols="auto" layout.
test('detail pane close and open-in-new buttons stay round in the narrow pane', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await openGallery(page)
  await page.locator('.seriesCard').first().locator('.mdi-eye').click()
  await expect(page.getByText('Metadata')).toBeVisible()

  for (const icon of ['mdi-close', 'mdi-open-in-new']) {
    const box = await page.locator(`button:has(.${icon})`).boundingBox()
    expect(box, icon).not.toBeNull()
    expect(Math.abs(box!.width - box!.height), `${icon} round`).toBeLessThan(1)
  }
})
