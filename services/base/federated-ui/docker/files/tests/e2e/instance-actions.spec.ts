import { test, expect, type Page } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  defaultMockData,
  localInstance,
  remoteInstance,
  VIEW_PATH,
} from './fixtures/mock-backend'

// The nearest ancestor v-row of a field label = that field's row (in both
// display and edit mode), avoiding RunnerInstances' outer wrapping v-row.
function fieldRow(page: Page, label: string) {
  return page
    .getByText(label, { exact: true })
    .locator('xpath=ancestor::*[contains(concat(" ", @class, " "), " v-row ")][1]')
}

test('edits a remote instance port and PUTs to the remote endpoint', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [remoteInstance] })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  await fieldRow(page, 'Network:').getByRole('button').click()
  await page.getByLabel('Port').fill('8443')

  const putReq = page.waitForRequest(
    (r) => /\/client\/remote-kaapana-instance/.test(r.url()) && r.method() === 'PUT',
  )
  // the save button is the only button in the row while in edit mode
  await fieldRow(page, 'Network:').getByRole('button').click()
  const body = (await putReq).postDataJSON()

  expect(body.instance_name).toBe('gpu-node-1')
  expect(String(body.port)).toBe('8443')
  // Only a successful PUT closes the edit row.
  await expect(page.getByLabel('Port')).toHaveCount(0)
})

test('edits a local instance and PUTs to the client endpoint', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [localInstance] })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: central-node')).toBeVisible()

  await fieldRow(page, 'Automatically sync remotes:').getByRole('button').click()
  await page.getByLabel('Check automatically for remote updates').click()

  const putReq = page.waitForRequest(
    (r) => /\/client\/client-kaapana-instance/.test(r.url()) && r.method() === 'PUT',
  )
  await fieldRow(page, 'Automatically sync remotes:').getByRole('button').click()
  const body = (await putReq).postDataJSON()

  expect(body.instance_name).toBe('central-node')
  expect(body.automatic_update).toBe(false) // toggled from true
})

test('a background poll mid-edit does not discard the unsaved field edit', async ({ page }) => {
  await page.clock.install()
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [remoteInstance] })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  await fieldRow(page, 'Network:').getByRole('button').click()
  await page.getByLabel('Port').fill('8443')

  // The poll refetch used to regenerate the working clone; it returns the
  // original port 443, so a clobber is observable in the next saved value.
  const poll = page.waitForRequest(
    (r) => /\/client\/get-kaapana-instances/.test(r.url()) && r.method() === 'POST',
  )
  await page.clock.runFor(15000)
  await poll

  // Assert on the PUT payload, not the visible field — Vuetify keeps its own
  // input state, so only the saved value pins the fix.
  const putReq = page.waitForRequest(
    (r) => /\/client\/remote-kaapana-instance/.test(r.url()) && r.method() === 'PUT',
  )
  await fieldRow(page, 'Network:').getByRole('button').click()
  const body = (await putReq).postDataJSON()
  expect(String(body.port)).toBe('8443')
})

test('deletes a remote instance after confirmation', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [remoteInstance] })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  await page.locator('button:has(.mdi-trash-can-outline)').click()
  await expect(page.getByText(/Are you sure you want to delete this instance/)).toBeVisible()

  const delReq = page.waitForRequest(
    (r) => /\/client\/kaapana-instance\?/.test(r.url()) && r.method() === 'DELETE',
  )
  await page.getByRole('button', { name: 'OK' }).click()
  expect((await delReq).url()).toContain('kaapana_instance_id=2')

  // Refetch after delete returns an empty list -> card is gone.
  await expect(page.getByText('Instance name: gpu-node-1')).toHaveCount(0)
})

test('a failed instance update keeps the field in edit mode and notifies', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [remoteInstance] })
  await page.route(/\/client\/remote-kaapana-instance/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: '{"detail":"instance is unreachable"}',
    }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: gpu-node-1')).toBeVisible()

  await fieldRow(page, 'Network:').getByRole('button').click()
  await page.getByLabel('Port').fill('8443')

  const putRes = page.waitForResponse(
    (r) => /\/client\/remote-kaapana-instance/.test(r.url()) && r.request().method() === 'PUT',
  )
  await fieldRow(page, 'Network:').getByRole('button').click()
  await putRes

  await expect(page.getByText('instance is unreachable')).toBeVisible()
  // A failed save must not look like a saved one: the row stays editable and
  // still holds the entered value.
  await expect(page.getByLabel('Port')).toHaveValue('8443')
  expect(pageErrors).toEqual([])
})

test('a failed dataset list keeps the previously loaded options and notifies', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [localInstance] })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Instance name: central-node')).toBeVisible()

  // Load the list once successfully, then close the row again.
  await fieldRow(page, 'Allowed Datasets:').getByRole('button').click()
  await page.locator('.v-select', { hasText: 'Allowed datasets' }).click()
  await expect(page.getByRole('option', { name: 'ds-project (project)' })).toBeVisible()
  await page.keyboard.press('Escape')
  const putRes = page.waitForResponse(
    (r) => /\/client\/client-kaapana-instance/.test(r.url()) && r.request().method() === 'PUT',
  )
  // Closing the row refetches too; let that land before the endpoint starts failing.
  const refetched = page.waitForResponse((r) => /\/client\/datasets/.test(r.url()))
  await fieldRow(page, 'Allowed Datasets:').getByRole('button').click()
  await putRes
  await refetched

  await page.route(/\/client\/datasets/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: '{"detail":"datasets are down"}',
    }),
  )
  const failed = page.waitForResponse((r) => /\/client\/datasets/.test(r.url()))
  await fieldRow(page, 'Allowed Datasets:').getByRole('button').click()
  await failed

  await expect(page.getByText('datasets are down')).toBeVisible()
  await page.locator('.v-select', { hasText: 'Allowed datasets' }).click()
  await expect(page.getByRole('option', { name: 'ds-project (project)' })).toBeVisible()
  expect(pageErrors).toEqual([])
})
