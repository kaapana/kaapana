import { test, expect, type Page } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import { collectPageErrors, dialog, openGallery, serverError, toasts } from './fixtures/helpers'

const LOOKUP = /\/kaapana-backend\/get-static-website-result-reports\?/
const REPORT = '**/reports/1.2.3.html'

function found(url = '/reports/1.2.3.html') {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ results: { '1.2.3': { found: true, url, object_name: 'x' } } }),
  }
}

/** Routes registered in `arrange` come after the mock backend's, so they win. */
async function openReport(page: Page, arrange: () => Promise<unknown> = async () => {}) {
  const data = makeDefaultMockData()
  data.seriesData['1.2.3'].metadata['Validation Results'] = {
    '00000000 ValidationErrors_integer': 3,
  }
  await openGallery(page, data)
  await arrange()
  await page.getByRole('button', { name: '3 validation errors — open report' }).click()
  const report = dialog(page, 'Validation report')
  await expect(report).toBeVisible()
  return report
}

async function downloadEntry(page: Page) {
  await dialog(page, 'Validation report').getByRole('button', { name: 'Report actions' }).click()
  return page.locator('.v-menu .v-list-item').filter({ hasText: 'Download report' })
}

const REPORT_BODY = {
  status: 200,
  contentType: 'text/html',
  body: '<html><body><h1>Report of 1.2.3</h1></body></html>',
}

test('a report that exists is shown and can be downloaded', async ({ page }) => {
  const report = await openReport(page, async () => {
    await page.route(LOOKUP, (r) => r.fulfill(found()))
    await page.route(REPORT, (r) => r.fulfill(REPORT_BODY))
  })

  await expect(report.getByText('Report of 1.2.3')).toBeVisible()
  const download = await downloadEntry(page)
  await expect(download).toBeVisible()
  await expect(download).not.toHaveClass(/v-list-item--disabled/)
})

test('a series without a report says so, and Download report says why it is unavailable', async ({
  page,
}) => {
  const report = await openReport(page)

  await expect(report.getByText('No validation report for this series')).toBeVisible()
  const download = await downloadEntry(page)
  await expect(download).toHaveClass(/v-list-item--disabled/)
  await expect(download).toContainText('No report exists for this series')
  await expect(toasts(page)).toHaveCount(0)
})

test('a failed lookup is a failure with Retry and Details, not "no report"', async ({ page }) => {
  let failing = true
  const report = await openReport(page, async () => {
    await page.route(LOOKUP, (r) => (failing ? r.fulfill(serverError('MinIO down')) : r.fulfill(found())))
    await page.route(REPORT, (r) => r.fulfill(REPORT_BODY))
  })

  const alert = report.getByTestId('report-lookup-alert')
  await expect(alert).toContainText('The validation report could not be looked up.')
  await expect(report.getByText('No validation report for this series')).toHaveCount(0)
  await page.waitForTimeout(700)
  await expect(toasts(page)).toHaveCount(0)

  await alert.getByRole('button', { name: 'Details' }).click()
  await expect(dialog(page, 'MinIO down')).toBeVisible()
  await dialog(page, 'MinIO down').getByRole('button', { name: 'Close' }).click()

  failing = false
  await alert.getByRole('button', { name: 'Try again' }).click()
  await expect(report.getByText('Report of 1.2.3')).toBeVisible()
})

test('a report that cannot be fetched says so inline, with a retry', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  let failing = true
  const report = await openReport(page, async () => {
    await page.route(LOOKUP, (r) => r.fulfill(found()))
    await page.route(REPORT, (r) =>
      failing ? r.fulfill({ status: 404, body: 'not found' }) : r.fulfill(REPORT_BODY),
    )
  })

  const alert = report.getByTestId('report-body-alert')
  await expect(alert).toContainText('The report could not be loaded.')
  await expect(report.getByText('Network response was not ok')).toHaveCount(0)
  await page.waitForTimeout(700)
  await expect(toasts(page)).toHaveCount(0)

  failing = false
  await alert.getByRole('button', { name: 'Try again' }).click()
  await expect(report.getByText('Report of 1.2.3')).toBeVisible()
  expect(pageErrors).toEqual([])
})
