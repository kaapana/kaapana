import { test, expect, type Page } from '@playwright/test'
import { cards, lastRequest, openView } from './fixtures/helpers'
import { entityId } from './fixtures/mock-backend'

async function addCondition(page: Page, field: string, operator: string, value: string) {
  await page.getByTestId('add-condition').first().click()
  const composer = page.getByTestId('condition-composer')
  await composer.getByRole('combobox', { name: 'Field' }).fill(field)
  await page.getByRole('option', { name: field }).first().click()
  await composer.locator('.composer-operator .v-field').click()
  await page.getByRole('option', { name: operator, exact: true }).click()
  await composer.getByRole('combobox').last().fill(value)
  await composer.getByRole('button', { name: 'Add condition' }).click()
}

test('a condition built in the editor filters the entities and is kept in the URL', async ({
  page,
}) => {
  const backend = await openView(page)
  await page.getByRole('button', { name: 'Filter' }).click()
  await addCondition(page, 'Metadata · series.modality', 'Equals', 'CT')

  await expect(cards(page)).toHaveCount(1)
  await expect(cards(page).first()).toContainText(entityId(3))
  expect(lastRequest(backend, 'POST', '/entities/query/index')?.body).toEqual({
    where: { type: 'filter', field: 'metadata.series.modality', op: 'eq', value: 'CT' },
  })
  await expect(page.getByTestId('condition')).toHaveText(/metadata\.series\.modality equals CT/)
  await expect(page).toHaveURL(/qa=1/)
  await expect(page.getByTestId('result-summary')).toHaveText('1 entity matches the filter')
})

test('a filter in the URL is applied on load and can be turned off and on', async ({ page }) => {
  const where = encodeURIComponent(
    JSON.stringify({
      type: 'filter',
      field: 'metadata.series.modality',
      op: 'in',
      value: ['CT', 'MR'],
    }),
  )
  await openView(page, undefined, { query: `?q=${where}&qa=1` })
  await expect(cards(page)).toHaveCount(2)

  const toggle = page.getByLabel('Apply filter')
  await toggle.click()
  await expect(cards(page)).toHaveCount(3)
  await expect(page).toHaveURL(/qa=0/)
  await toggle.click()
  await expect(cards(page)).toHaveCount(2)
})

test('a filter can be entered as JSON and cleared', async ({ page }) => {
  await openView(page)
  await page.getByRole('button', { name: 'Filter' }).click()
  await page.getByRole('button', { name: 'JSON', exact: true }).click()
  await page
    .getByRole('textbox', { name: 'Filter as JSON' })
    .fill(JSON.stringify({ type: 'filter', field: 'id', op: 'ends_with', value: '2' }))
  await page.getByRole('button', { name: 'Apply filter' }).click()
  await expect(cards(page)).toHaveCount(1)

  await page.getByRole('button', { name: 'Clear filter' }).click()
  await expect(cards(page)).toHaveCount(3)
  await expect(page).not.toHaveURL(/q=/)
})

test('invalid JSON is explained at the field', async ({ page }) => {
  await openView(page)
  await page.getByRole('button', { name: 'Filter' }).click()
  await page.getByRole('button', { name: 'JSON', exact: true }).click()
  await page.getByRole('textbox', { name: 'Filter as JSON' }).fill('{"field": "id"}')
  await page.getByRole('button', { name: 'Apply filter' }).click()
  await expect(page.getByText('The filter needs a "type" of "filter" or "group"')).toBeVisible()
})

test('a rejected filter is reported with the backend message', async ({ page }) => {
  await openView(page, undefined, {
    routes: (target) =>
      target.route(
        (url) => url.pathname.endsWith('/entities/query/index'),
        (route) =>
          route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({ detail: "Unsupported query field 'foo'" }),
          }),
      ),
  })
  await page.getByRole('button', { name: 'Filter' }).click()
  await page.getByRole('button', { name: 'JSON', exact: true }).click()
  await page
    .getByRole('textbox', { name: 'Filter as JSON' })
    .fill('{"type": "filter", "field": "foo", "op": "eq", "value": 1}')
  await page.getByRole('button', { name: 'Apply filter' }).click()
  await expect(
    page.locator('.vue-notification-wrapper').filter({ hasText: "Unsupported query field 'foo'" }),
  ).toBeVisible()
  await expect(cards(page)).toHaveCount(3)
})
