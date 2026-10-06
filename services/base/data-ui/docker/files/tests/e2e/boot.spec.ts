import { test, expect } from '@playwright/test'
import { cards, openView } from './fixtures/helpers'
import { PROJECT_SLUG, defaultMockData, entityId } from './fixtures/mock-backend'

test('lists the entities of the project with their metadata', async ({ page }) => {
  await openView(page)
  await expect(page.getByRole('heading', { level: 1, name: 'Data' })).toBeVisible()
  await expect(cards(page)).toHaveCount(3)
  await expect(cards(page).first()).toContainText(entityId(1))
  await expect(cards(page).first()).toContainText('modality: MR')
  await expect(page.getByTestId('result-summary')).toHaveText('3 entities')
})

test('requests, previews and live updates carry the project prefix', async ({ page }) => {
  const backend = await openView(page)
  const prefix = `/project/${PROJECT_SLUG}/data-api/v1/`
  expect(backend.requests.length).toBeGreaterThan(0)
  for (const request of backend.requests) {
    expect(request.path.startsWith(prefix), request.path).toBe(true)
  }
  await expect.poll(() => backend.socketUrls).toEqual([`${prefix}ws/events`])
  const thumbnail = cards(page).first().locator('img')
  await expect(thumbnail).toHaveAttribute('src', new RegExp(`^${prefix}entities/`))
})

test('served without a project, requests stay unprefixed', async ({ page }) => {
  const backend = await openView(page, defaultMockData(), { scoped: false })
  for (const request of backend.requests) {
    expect(request.path.startsWith('/data-api/v1/'), request.path).toBe(true)
  }
})

test('an entity created elsewhere appears through the live update', async ({ page }) => {
  const data = defaultMockData(2)
  const backend = await openView(page, data)
  await expect(cards(page)).toHaveCount(2)
  data.entities.push({ ...data.entities[0], id: entityId(9) })
  backend.push({ resource: 'data_entity', action: 'created', data: { id: entityId(9) } })
  await expect(cards(page)).toHaveCount(3)
  await expect(cards(page).last()).toContainText(entityId(9))
})

test('a deleted entity disappears through the live update', async ({ page }) => {
  const backend = await openView(page)
  backend.push({ resource: 'data_entity', action: 'deleted', data: { id: entityId(2) } })
  await expect(cards(page)).toHaveCount(2)
  await expect(page.getByText(entityId(2))).toHaveCount(0)
})
