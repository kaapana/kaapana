import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()
})

test('search filters the list down to matching extensions', async ({ page }) => {
  await page.getByRole('textbox', { name: 'Search' }).fill('JupyterLab')

  await expect(page.getByText('JupyterLab')).toBeVisible()
  await expect(page.getByText('MITK Workbench')).toHaveCount(0)
  await expect(page.getByText('nnU-Net Training')).toHaveCount(0)
})

test('enabling the Experimental maturity filter reveals experimental extensions', async ({
  page,
}) => {
  await expect(page.getByText('Experimental Tool')).toHaveCount(0)

  await page.getByTestId('filter-maturity').click()
  await page.getByRole('checkbox', { name: 'Experimental' }).check()

  await expect(page.getByText('Experimental Tool')).toBeVisible()
})

test('toggling the kind filter hides applications', async ({ page }) => {
  await page.getByTestId('filter-kind').click()
  await page.getByRole('checkbox', { name: 'Applications' }).uncheck()

  // Applications drop out; the workflow (dag) extension remains.
  await expect(page.getByText('MITK Workbench')).toHaveCount(0)
  await expect(page.getByText('JupyterLab')).toHaveCount(0)
  await expect(page.getByText('nnU-Net Training')).toBeVisible()
})
