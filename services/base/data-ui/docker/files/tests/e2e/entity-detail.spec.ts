import { test, expect } from '@playwright/test'
import {
  lastRequest,
  openEntity,
  openFailureDetails,
  openView,
  recordShellMessages,
  toasts,
} from './fixtures/helpers'
import { PROJECT_SLUG, defaultMockData, entity, entityId } from './fixtures/mock-backend'

test('shows the overview, artifacts, storage and hierarchy of an entity', async ({ page }) => {
  const data = defaultMockData()
  data.entities[0] = entity(1, { child_ids: [entityId(2)] })
  data.entities[1] = entity(2, { parent_id: entityId(1) })
  await openView(page, data)
  const detail = await openEntity(page, entityId(1))
  await expect(detail.getByText('Storage locations')).toBeVisible()

  await detail.getByRole('tab', { name: 'Artifacts (1)' }).click()
  const download = detail.getByRole('link', { name: 'Download thumb-1.png' })
  await expect(download).toHaveAttribute(
    'href',
    `/project/${PROJECT_SLUG}/data-api/v1/entities/${entityId(1)}/metadata/series/artifacts/thumbnail`,
  )

  await detail.getByRole('tab', { name: 'Storage (1)' }).click()
  await expect(detail.getByText('study_uid: 1.2.1')).toBeVisible()

  await detail.getByRole('tab', { name: 'Hierarchy (1)' }).click()
  await detail.getByRole('listitem', { name: `Show child entity ${entityId(2)}` }).click()
  await expect(page.getByTestId('entity-detail')).toContainText(entityId(2))
})

test('an edited metadata entry is saved with its artifacts kept', async ({ page }) => {
  const backend = await openView(page)
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: /^series/ }).click()
  await detail.getByLabel('Description').fill('Edited series')
  await expect(detail.getByText('Unsaved changes')).toBeVisible()
  await detail.getByRole('button', { name: 'Save entry' }).click()

  await expect(toasts(page).filter({ hasText: 'Metadata entry saved' })).toBeVisible()
  const request = lastRequest(backend, 'POST', `/entities/${entityId(1)}/metadata`)
  expect(request?.body).toMatchObject({
    key: 'series',
    data: { modality: 'MR', description: 'Edited series', slices: 11 },
    artifacts: [{ id: 'thumbnail' }],
  })
  await expect(detail.getByText('Unsaved changes')).toHaveCount(0)
})

test('a required field explains what is missing and blocks the save', async ({ page }) => {
  const backend = await openView(page)
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: /^series/ }).click()
  await detail.getByRole('button', { name: 'Clear Modality' }).click()
  await detail.getByRole('button', { name: 'Save entry' }).click()
  await expect(detail.getByText('Enter Modality; the field is required.')).toBeVisible()
  expect(lastRequest(backend, 'POST', `/entities/${entityId(1)}/metadata`)).toBeUndefined()
})

test('closing with unsaved changes asks before discarding them', async ({ page }) => {
  const shell = await recordShellMessages(page)
  await openView(page)
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: /^series/ }).click()
  await detail.getByLabel('Description').fill('Not saved')
  await expect
    .poll(async () => (await shell()).filter((m) => m.type === 'kaapana:view-dirty').at(-1)?.dirty)
    .toBe(true)

  await detail.getByRole('button', { name: 'Close' }).first().click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'Discard unsaved changes?' })
  await expect(confirm.getByRole('button', { name: 'Keep editing' })).toBeFocused()
  await confirm.getByRole('button', { name: 'Keep editing' }).click()
  await expect(confirm).toBeHidden()
  await expect(detail.getByLabel('Description')).toHaveValue('Not saved')

  await page.keyboard.press('Escape')
  await page
    .getByRole('dialog')
    .filter({ hasText: 'Discard unsaved changes?' })
    .getByRole('button', { name: 'Discard changes' })
    .click()
  await expect(page.getByTestId('entity-detail')).toHaveCount(0)
  await expect
    .poll(async () => (await shell()).filter((m) => m.type === 'kaapana:view-dirty').at(-1)?.dirty)
    .toBe(false)
})

test('a new entry can be added for a registered key the entity does not have yet', async ({
  page,
}) => {
  const backend = await openView(page)
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: 'Add entry' }).click()
  const add = detail.getByTestId('add-metadata')
  await add.getByRole('combobox', { name: 'Key' }).click()
  await expect(page.getByRole('option', { name: 'series' })).toHaveCount(0)
  await page.getByRole('option', { name: 'notes' }).click()
  await add.getByLabel('Text').fill('Reviewed')
  await add.getByRole('button', { name: 'Add entry' }).click()

  await expect(toasts(page).filter({ hasText: 'Metadata entry added' })).toBeVisible()
  expect(lastRequest(backend, 'POST', `/entities/${entityId(1)}/metadata`)?.body).toEqual({
    key: 'notes',
    data: { text: 'Reviewed' },
    artifacts: [],
  })
  await expect(detail.getByRole('tab', { name: 'Metadata (2)' })).toBeVisible()
})

test('removing an entry is confirmed and names the files deleted with it', async ({ page }) => {
  const backend = await openView(page)
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: /^series/ }).click()
  await detail.getByRole('button', { name: 'Remove entry' }).click()

  const confirm = page.getByRole('dialog').filter({ hasText: 'Remove metadata entry?' })
  await expect(confirm).toContainText('Its 1 artifact file is deleted as well.')
  await confirm.getByRole('button', { name: 'Remove entry' }).click()
  await expect(toasts(page).filter({ hasText: 'Metadata entry removed' })).toBeVisible()
  expect(lastRequest(backend, 'DELETE', `/entities/${entityId(1)}/metadata/series`)).toBeTruthy()
})

test('the permissions entry cannot be removed inside a project', async ({ page }) => {
  const data = defaultMockData()
  data.schemas.permissions = { type: 'object', properties: { project: { type: 'string' } } }
  data.entities[0].metadata.push({ key: 'permissions', data: { project: 'p-1' }, artifacts: [] })
  await openView(page, data)
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: /^permissions/ }).click()
  await expect(detail.getByRole('button', { name: 'Remove entry' }).last()).toBeDisabled()
})

test('a failed save is reported with the backend detail on demand', async ({ page }) => {
  await openView(page, undefined, {
    routes: (target) =>
      target.route(
        (url) => url.pathname.endsWith('/metadata') && url.pathname.includes('/entities/'),
        (route) =>
          route.request().method() === 'POST'
            ? route.fulfill({
                status: 400,
                contentType: 'application/json',
                body: JSON.stringify({
                  detail: "Metadata entry violates schema: 'XA' is not one of",
                }),
              })
            : route.fallback(),
      ),
  })
  const detail = await openEntity(page, entityId(1))
  await detail.getByRole('button', { name: /^series/ }).click()
  await detail.getByLabel('Description').fill('x')
  await detail.getByRole('button', { name: 'Save entry' }).click()
  const details = await openFailureDetails(page, 'Metadata entry not saved')
  await expect(details).toContainText('400')
  await expect(details).toContainText('violates schema')
})
