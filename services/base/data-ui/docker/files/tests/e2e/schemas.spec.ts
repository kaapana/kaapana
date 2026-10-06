import { test, expect, type Page } from '@playwright/test'
import { lastRequest, openView, toasts } from './fixtures/helpers'

async function openSchemas(page: Page) {
  await page.getByRole('button', { name: 'Metadata schemas' }).click()
  const schemas = page.getByRole('dialog').filter({ hasText: 'Metadata schemas' })
  await expect(schemas.getByRole('textbox', { name: 'JSON Schema' })).toBeVisible()
  return schemas
}

test('a new schema can be registered', async ({ page }) => {
  const backend = await openView(page)
  const schemas = await openSchemas(page)
  await schemas.getByTestId('new-schema').click()
  await schemas.getByRole('textbox', { name: 'Key' }).fill('acquisition')
  await schemas
    .getByRole('textbox', { name: 'JSON Schema' })
    .fill('{"type": "object", "properties": {"site": {"type": "string"}}}')
  await schemas.getByRole('button', { name: 'Register schema' }).click()

  await expect(toasts(page).filter({ hasText: 'Schema registered' })).toBeVisible()
  expect(lastRequest(backend, 'POST', '/metadata/keys/acquisition')?.body).toEqual({
    type: 'object',
    properties: { site: { type: 'string' } },
  })
  await expect(schemas.getByRole('listitem').filter({ hasText: 'acquisition' })).toBeVisible()
})

test('key and JSON problems are explained at the fields', async ({ page }) => {
  const backend = await openView(page)
  const schemas = await openSchemas(page)
  await schemas.getByTestId('new-schema').click()
  await schemas.getByRole('textbox', { name: 'Key' }).fill('series')
  await schemas.getByRole('textbox', { name: 'JSON Schema' }).fill('{"type": ')
  await schemas.getByRole('button', { name: 'Register schema' }).click()

  await expect(schemas.getByText('A schema with the key "series" already exists.')).toBeVisible()
  await expect(schemas.getByText(/The text is not valid JSON/)).toBeVisible()
  expect(lastRequest(backend, 'POST', '/metadata/keys/series')).toBeUndefined()
})

test('a schema in use cannot be deleted and the reason is shown', async ({ page }) => {
  await openView(page)
  const schemas = await openSchemas(page)
  await schemas.getByRole('button', { name: 'Delete schema series' }).click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'Delete schema?' })
  await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
  await confirm.getByRole('button', { name: 'Delete schema' }).click()
  await expect(toasts(page).filter({ hasText: 'Schema not deleted' })).toContainText(
    'it is used by 3 entity/entities',
  )
})

test('an unused schema is deleted after confirmation', async ({ page }) => {
  const backend = await openView(page)
  const schemas = await openSchemas(page)
  await schemas.getByRole('button', { name: 'Delete schema notes' }).click()
  await page
    .getByRole('dialog')
    .filter({ hasText: 'Delete schema?' })
    .getByRole('button', { name: 'Delete schema' })
    .click()
  await expect(toasts(page).filter({ hasText: 'Schema deleted' })).toBeVisible()
  expect(lastRequest(backend, 'DELETE', '/metadata/keys/notes')).toBeTruthy()
  await expect(schemas.getByRole('listitem').filter({ hasText: 'notes' })).toHaveCount(0)
})

test('closing with an unsaved schema edit asks first', async ({ page }) => {
  await openView(page)
  const schemas = await openSchemas(page)
  await schemas.getByRole('textbox', { name: 'JSON Schema' }).fill('{"type": "object"}')
  await schemas.getByRole('button', { name: 'Close' }).click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'Discard unsaved changes?' })
  await expect(confirm.getByRole('button', { name: 'Keep editing' })).toBeFocused()
  await confirm.getByRole('button', { name: 'Discard changes' }).click()
  await expect(schemas).toBeHidden()
})

test('the schema of an entry opens from the entity detail', async ({ page }) => {
  await openView(page)
  await page
    .getByTestId('entity-card')
    .first()
    .getByRole('button', { name: /Show details/ })
    .click()
  const detail = page.getByTestId('entity-detail')
  await detail.getByRole('button', { name: /^series/ }).click()
  await detail.getByRole('button', { name: 'View schema' }).click()
  const schemas = page.getByRole('dialog').filter({ hasText: 'Metadata schemas' })
  await expect(schemas.getByRole('heading', { name: 'series' })).toBeVisible()
})
