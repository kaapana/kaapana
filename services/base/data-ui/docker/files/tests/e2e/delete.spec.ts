import { test, expect } from '@playwright/test'
import { card, cards, lastRequest, openEntity, openView, toasts } from './fixtures/helpers'
import { entityId } from './fixtures/mock-backend'

test('deleting an entity is confirmed with the safe action focused', async ({ page }) => {
  const backend = await openView(page)
  await card(page, entityId(2))
    .getByRole('button', { name: `Delete entity ${entityId(2)}` })
    .click()

  const confirm = page.getByRole('dialog').filter({ hasText: 'Delete entity?' })
  await expect(confirm).toContainText('together with its metadata entries and 1 artifact file')
  await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
  await expect(confirm.getByRole('button', { name: 'Delete entity' })).toHaveClass(
    /text-error|bg-error/,
  )
  await confirm.getByRole('button', { name: 'Delete entity' }).click()

  await expect(toasts(page).filter({ hasText: 'Entity deleted' })).toBeVisible()
  await expect(cards(page)).toHaveCount(2)
  expect(lastRequest(backend, 'DELETE', `/entities/${entityId(2)}`)).toBeTruthy()
})

test('cancelling keeps the entity and returns focus', async ({ page }) => {
  const backend = await openView(page)
  const remove = card(page, entityId(1)).getByRole('button', {
    name: `Delete entity ${entityId(1)}`,
  })
  await remove.focus()
  await page.keyboard.press('Enter')
  await page
    .getByRole('dialog')
    .filter({ hasText: 'Delete entity?' })
    .getByRole('button', { name: 'Cancel' })
    .click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(remove).toBeFocused()
  expect(lastRequest(backend, 'DELETE', `/entities/${entityId(1)}`)).toBeUndefined()
  await expect(cards(page)).toHaveCount(3)
})

test('deleting from the detail dialog closes it', async ({ page }) => {
  await openView(page)
  const detail = await openEntity(page, entityId(3))
  await detail.getByRole('button', { name: 'Delete entity' }).click()
  await page
    .getByRole('dialog')
    .filter({ hasText: 'Delete entity?' })
    .getByRole('button', { name: 'Delete entity' })
    .click()
  await expect(page.getByTestId('entity-detail')).toHaveCount(0)
  await expect(cards(page)).toHaveCount(2)
})

test('a failed deletion keeps the entity and explains why', async ({ page }) => {
  await openView(page, undefined, {
    routes: (target) =>
      target.route(
        (url) => url.pathname.endsWith(`/entities/${entityId(1)}`),
        (route) =>
          route.request().method() === 'DELETE'
            ? route.fulfill({
                status: 404,
                contentType: 'application/json',
                body: '{"detail":"Entity not found"}',
              })
            : route.fallback(),
      ),
  })
  await card(page, entityId(1))
    .getByRole('button', { name: `Delete entity ${entityId(1)}` })
    .click()
  await page
    .getByRole('dialog')
    .filter({ hasText: 'Delete entity?' })
    .getByRole('button', { name: 'Delete entity' })
    .click()
  await expect(toasts(page).filter({ hasText: 'Entity not deleted' })).toContainText(
    'Entity not found',
  )
  await expect(cards(page)).toHaveCount(3)
})
