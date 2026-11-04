import { test, expect, type Page } from '@playwright/test'
import { openRuns, runRow, runRows } from './fixtures/helpers'

function searchInput(page: Page) {
  return page.getByRole('search').getByRole('textbox')
}

function suggestions(page: Page) {
  return page.locator('.v-overlay--active')
}

async function addFilter(page: Page, key: string, value: string, operator: string | null = '=') {
  await searchInput(page).click()
  await suggestions(page).getByText(key, { exact: true }).click()
  if (operator) await suggestions(page).getByText(operator, { exact: true }).click()
  await searchInput(page).fill(value)
  await searchInput(page).press('Enter')
}

async function search(page: Page) {
  await page.getByRole('search').getByRole('button', { name: 'Search', exact: true }).click()
}

test.describe('query builder', () => {
  test('a status filter is built from key and value and shown as a token', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*=\s*Error/)
    await search(page)
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('new filters are joined with AND', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await addFilter(page, 'Status', 'Running')
    await expect(page.getByTestId('filter-connector')).toHaveText('AND')
    await search(page)
    await expect(runRows(page)).toHaveCount(0)
  })

  test('switching a connector to OR matches any filter of the group', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await addFilter(page, 'Status', 'Running')
    await page
      .getByRole('button', { name: 'Change AND before filter Status = Running to OR' })
      .click()
    await expect(page.getByTestId('filter-connector')).toHaveText('OR')
    await expect(page.getByTestId('filter-group')).toHaveCount(1)
    await search(page)
    await expect(runRows(page)).toHaveCount(2)
  })

  test('an OR group must match together with the filters joined by AND', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Running')
    await addFilter(page, 'Status', 'Error')
    await page
      .getByRole('button', { name: 'Change AND before filter Status = Error to OR' })
      .click()
    await addFilter(page, 'Workflow', 'Registration')
    await expect(page.getByTestId('filter-group')).toHaveCount(2)
    await search(page)
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('removing the first filter of an OR group keeps the group', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Workflow', 'Registration')
    await addFilter(page, 'Status', 'Running')
    await addFilter(page, 'Status', 'Error')
    await page
      .getByRole('button', { name: 'Change AND before filter Status = Error to OR' })
      .click()
    await page.getByRole('button', { name: 'Remove filter Status = Running' }).click()
    await expect(page.getByTestId('filter-connector')).toHaveText('AND')
    await search(page)
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('!= excludes a value', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error', '!=')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*!=\s*Error/)
    await search(page)
    await expect(runRows(page)).toHaveCount(2)
    await expect(runRow(page, 3)).toHaveCount(0)
  })

  test('several != filters of the same key exclude all of them', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error', '!=')
    await addFilter(page, 'Status', 'Running', '!=')
    await search(page)
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 1)).toBeVisible()
  })

  test('= and != filters of the same key combine', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Workflow', 'Segmentation')
    await addFilter(page, 'Workflow', 'Registration')
    await page
      .getByRole('button', { name: 'Change AND before filter Workflow = Registration to OR' })
      .click()
    await addFilter(page, 'Status', 'Running', '!=')
    await search(page)
    await expect(runRows(page)).toHaveCount(2)
    await expect(runRow(page, 2)).toHaveCount(0)
  })

  test('a new operator asks for the value again', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await page.getByRole('button', { name: 'Change the operator of filter Status = Error' }).click()
    await expect(searchInput(page)).toHaveAccessibleName('Operator for Status')
    await suggestions(page).getByText('!=', { exact: true }).click()
    await expect(searchInput(page)).toHaveAccessibleName('Value for Status')
    await searchInput(page).fill('Running')
    await searchInput(page).press('Enter')
    await expect(page.getByTestId('filter-token')).toHaveText(/Status\s*!=\s*Running/)
    await search(page)
    await expect(runRows(page)).toHaveCount(2)
  })

  test('filters apply only after Search or Enter in the empty field', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await expect(page.getByTestId('filter-token')).toHaveCount(1)
    await expect(runRows(page)).toHaveCount(3)
    await searchInput(page).press('Enter')
    await expect(runRows(page)).toHaveCount(1)
  })

  test('the clear button removes all filters at once and keeps the focus', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Status', 'Error')
    await search(page)
    await page.getByRole('button', { name: 'Clear all filters' }).click()
    await expect(page.getByTestId('filter-token')).toHaveCount(0)
    await expect(searchInput(page)).toBeFocused()
    await expect(runRows(page)).toHaveCount(3)
  })

  test('filters of different keys must all match', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Workflow', 'Segmentation')
    await addFilter(page, 'Status', 'Completed')
    await search(page)
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

  test('several status counts add status filters joined with OR', async ({ page }) => {
    await openRuns(page)
    const summary = page.getByTestId('status-summary')
    await summary.getByText('Running · 1').click()
    await summary.getByText('Error · 1').click()
    await expect(page.getByTestId('filter-connector')).toHaveText('OR')
    await expect(runRows(page)).toHaveCount(2)
  })

  test('free text searches title, status and ids', async ({ page }) => {
    await openRuns(page)
    await searchInput(page).fill('regist')
    await searchInput(page).press('Enter')
    await expect(runRows(page)).toHaveCount(1)
    await expect(runRow(page, 3)).toBeVisible()
  })

  test('date filters take YYYY-MM-DD', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Created after', '2026-09-29', null)
    await search(page)
    await expect(runRows(page)).toHaveCount(2)
  })

  test('date filters fill in their only operator and pick the date in a calendar', async ({
    page,
  }) => {
    await openRuns(page)
    await searchInput(page).click()
    await suggestions(page).getByText('Created before', { exact: true }).click()
    await expect(searchInput(page)).toHaveAccessibleName('Value for Created before')
    await expect(suggestions(page).locator('.v-date-picker')).toBeVisible()
    await suggestions(page)
      .locator('.v-date-picker')
      .getByText('29', { exact: true })
      .first()
      .click()
    await expect(page.getByTestId('filter-token')).toHaveText(/Created before\s*=\s*\d{4}-\d{2}-29/)
  })

  test('date filters reject anything but YYYY-MM-DD', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Created on', 'yesterday', null)
    await expect(page.getByTestId('filter-token')).toHaveCount(0)
    await searchInput(page).fill('30.09.2026')
    await searchInput(page).press('Enter')
    await expect(page.getByTestId('filter-token')).toHaveCount(0)
    await searchInput(page).fill('2026-09-30')
    await searchInput(page).press('Enter')
    await expect(page.getByTestId('filter-token')).toHaveText(/Created on\s*=\s*2026-09-30/)
    await search(page)
    await expect(runRows(page)).toHaveCount(1)
  })

  test('task is no filter key', async ({ page }) => {
    await openRuns(page)
    await searchInput(page).click()
    await expect(suggestions(page).getByText('Status', { exact: true })).toBeVisible()
    await expect(suggestions(page).getByText('Task', { exact: true })).toHaveCount(0)
  })

  test('no match offers to clear the filters', async ({ page }) => {
    await openRuns(page)
    await addFilter(page, 'Run ID', '999')
    await search(page)
    await page.getByRole('button', { name: 'Clear filters' }).click()
    await search(page)
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
      token.getByRole('button', { name: 'Change the operator of filter Status = Error' }),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clear all filters' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeVisible()
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
