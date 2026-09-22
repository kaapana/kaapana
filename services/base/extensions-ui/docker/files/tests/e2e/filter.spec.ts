import { test, expect } from '@playwright/test'
import { openView, row } from './fixtures/helpers'

test.beforeEach(({ page }) => openView(page))

test('search filters the list down to matching extensions', async ({ page }) => {
  await page.getByLabel('Search').fill('JupyterLab')

  await expect(row(page, 'JupyterLab')).toBeVisible()
  await expect(row(page, 'MITK Workbench')).toHaveCount(0)
  await expect(row(page, 'nnU-Net Training')).toHaveCount(0)
})

test('enabling the Experimental maturity filter reveals experimental extensions', async ({
  page,
}) => {
  await expect(row(page, 'Experimental Tool')).toHaveCount(0)

  await page.getByTestId('filter-maturity').click()
  await page.getByRole('checkbox', { name: 'Experimental' }).check()

  await expect(row(page, 'Experimental Tool')).toBeVisible()
})

test('toggling the kind filter hides applications', async ({ page }) => {
  await page.getByTestId('filter-kind').click()
  await page.getByRole('checkbox', { name: 'Applications' }).uncheck()

  // Applications drop out; the workflow (dag) extension remains.
  await expect(row(page, 'MITK Workbench')).toHaveCount(0)
  await expect(row(page, 'JupyterLab')).toHaveCount(0)
  await expect(row(page, 'nnU-Net Training')).toBeVisible()
})
