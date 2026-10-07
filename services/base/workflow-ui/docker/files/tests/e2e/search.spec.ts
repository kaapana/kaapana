import { test, expect, type Page } from '@playwright/test'
import { openRuns, runRow, runRows } from './fixtures/helpers'

function searchInput(page: Page) {
  return page.getByRole('search').getByRole('textbox')
}

function suggestions(page: Page) {
  return page.locator('.v-overlay--active')
}

async function addFilter(page: Page, field: string, value: string, operator = '=') {
  await searchInput(page).click()
  await suggestions(page).getByText(field, { exact: true }).click()
  await suggestions(page).getByText(operator, { exact: true }).click()
  await searchInput(page).fill(value)
  await searchInput(page).press('Enter')
}

test.describe('query builder', () => {
  test('a status filter is built from field and value and shown as a token', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*=\s*Error/)
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('filters of the same field match any of them', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await addFilter(page, 'Status', 'Running')
    await expect(runRows(page)).toHaveCount(2)
  })

  test('!= excludes a value', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error', '!=')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*!=\s*Error/)
    await expect(runRows(page)).toHaveCount(2)
    await expect(runRow(page, 3)).toHaveCount(0)
  })

  test('several != filters of the same field exclude all of them', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error', '!=')
    await addFilter(page, 'Status', 'Running', '!=')
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 1)).toBeVisible()
  })

  test('= and != filters of the same field combine', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Workflow', 'Segmentation')
    await addFilter(page, 'Workflow', 'Registration')
    await addFilter(page, 'Status', 'Running', '!=')
    await expect(runRows(page)).toHaveCount(2)
    await expect(runRow(page, 2)).toHaveCount(0)
  })

  test('the operator of a token switches between = and !=', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await page
      .getByRole('button', { name: 'Change the operator of filter Status = Error to !=' })
      .click()
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*!=\s*Error/)
    await expect(runRows(page)).toHaveCount(2)
  })

  test('filters of different fields must all match', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Workflow', 'Segmentation')
    await addFilter(page, 'Status', 'Completed')
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 1)).toBeVisible()
  })

  test('the status counts toggle a status filter in the query builder', async ({ page }) => {
    await openRuns(page)
    const chip = page.getByTestId('status-summary').getByText('Running · 1')
    await chip.click()
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*=\s*Running/)
    await expect(runRows(page)).toHaveCount(1)
    await chip.click()
    await expect(page.getByTestId('filter-token')).toHaveCount(0)
    await expect(runRows(page)).toHaveCount(3)
  })

  test('free text searches title, status and ids', async ({ page }) => {
    await openRuns(page)
    await searchInput(page).fill('regist')
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('date filters accept German dates', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Created since', '30.09.2026')
    await expect(runRows(page)).toHaveCount(2)
  })

  test('no match offers to clear the filters', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Run ID', '999')
    await page.getByRole('button', { name: 'Clear filters' }).click()
    await expect(runRows(page)).toHaveCount(3)
  })

  test('the keyboard alone can add and remove filters', async ({ page }) => {
    await openRuns(page)
    await searchInput(page).focus()
    await page.keyboard.type('status')
    await page.keyboard.press('Enter')
    await expect(searchInput(page)).toHaveAccessibleName('Operator for Status')
    await page.keyboard.press('Enter')
    await page.keyboard.type('error')
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*=\s*Error/)
    await expect(searchInput(page)).toBeFocused()

    await page.keyboard.type('status')
    await page.keyboard.press('Enter')
    await page.keyboard.type('!=')
    await page.keyboard.press('Enter')
    await page.keyboard.type('completed')
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('filter-token').nth(1)).toHaveText(/Status\s*!=\s*Completed/)

    await page.keyboard.press('Backspace')
    await page.keyboard.press('Backspace')
    await expect(page.getByTestId('filter-token')).toHaveCount(0)
  })

  test('every control of the query builder has an accessible name', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await expect(searchInput(page)).toHaveAccessibleName('Search or filter workflow runs')
    const token = page.getByTestId('filter-token')
    await expect(token.getByRole('button', { name: 'Remove filter Status = Error' })).toBeVisible()
    await expect(
      token.getByRole('button', { name: 'Change the value of filter Status = Error' }),
    ).toBeVisible()
    await expect(
      token.getByRole('button', { name: 'Change the operator of filter Status = Error to !=' }),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clear all filters' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: /Sort runs, currently by Created/ }),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'How to filter runs' })).toBeVisible()
  })

  test('a token value can be changed in place', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await page.getByRole('button', { name: 'Change the value of filter Status = Error' }).click()
    await searchInput(page).fill('Completed')
    await searchInput(page).press('Enter')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*=\s*Completed/)
    await expect(page.getByTestId('filter-token')).toHaveCount(1)
  })

  test('sorting by workflow orders the rows by title', async ({ page }) => {
    await openRuns(page)
    await page.getByRole('button', { name: /Sort runs/ }).click()
    await page.locator('.v-overlay--active').getByText('Workflow', { exact: true }).click()
    await expect(runRows(page).nth(0)).toContainText('Segmentation')
    await expect(runRows(page).nth(2)).toContainText('Registration')
  })
})
