import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('opens the add-remote dialog with Manual and Paste Config tabs', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [] })
  await page.goto(VIEW_PATH)

  await page.getByRole('button', { name: 'add remote' }).click()
  await expect(page.getByText('Remote Instance', { exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Manual' })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Paste Config' })).toBeVisible()
})

test('opens the add-remote dialog and blocks an empty submit', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [] })
  await page.goto(VIEW_PATH)

  await page.getByRole('button', { name: 'add remote' }).click()
  await expect(page.getByText('Remote Instance', { exact: true })).toBeVisible()

  let posted = false
  page.on('request', (r) => {
    if (/\/client\/remote-kaapana-instance/.test(r.url()) && r.method() === 'POST') posted = true
  })

  // name/host/token are the three required fields
  await page.getByRole('button', { name: 'submit' }).click()
  await expect(page.getByText('This field is required')).toHaveCount(3)
  await page.waitForTimeout(300)
  expect(posted).toBe(false)
})

test('validates the Manual fields even when submitting from the Paste Config tab', async ({
  page,
}) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [] })
  await page.goto(VIEW_PATH)

  await page.getByRole('button', { name: 'add remote' }).click()
  // Never visit Manual: its fields must stay mounted (eager) for validation to
  // block the submit. Assert on the request NOT firing — the error messages
  // live in the now-hidden Manual pane, so visibility can't be checked.
  await page.getByRole('tab', { name: 'Paste Config' }).click()

  let posted = false
  page.on('request', (r) => {
    if (/\/client\/remote-kaapana-instance/.test(r.url()) && r.method() === 'POST') posted = true
  })

  await page.getByRole('button', { name: 'submit' }).click()
  await page.waitForTimeout(300)
  expect(posted).toBe(false)
})

test('submits the filled remote-instance definition and shows the new card', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [] })
  await page.goto(VIEW_PATH)

  await page.getByRole('button', { name: 'add remote' }).click()
  await page.getByLabel('Instance name').fill('new-remote')
  await page.getByLabel('Host').fill('192.168.1.10')
  await page.getByLabel('Token').fill('tok-123')

  const postReq = page.waitForRequest(
    (r) => /\/client\/remote-kaapana-instance/.test(r.url()) && r.method() === 'POST',
  )
  await page.getByRole('button', { name: 'submit' }).click()
  const body = (await postReq).postDataJSON()

  expect(body).toMatchObject({
    instance_name: 'new-remote',
    host: '192.168.1.10',
    token: 'tok-123',
    port: 443,
    fernet_key: 'deactivated',
    ssl_check: false,
  })

  // Dialog closes and the refetch surfaces the created instance.
  await expect(page.getByText('Remote Instance', { exact: true })).toBeHidden()
  await expect(page.getByText('Instance name: new-remote')).toBeVisible()
})

test('pasting JSON in the Paste Config tab fills the Manual fields and submits', async ({
  page,
}) => {
  await seedShellState(page)
  await installMockBackend(page, { ...defaultMockData, instances: [] })
  await page.goto(VIEW_PATH)

  await page.getByRole('button', { name: 'add remote' }).click()
  await page.getByRole('tab', { name: 'Paste Config' }).click()

  // Valid double-quoted JSON: the watch parses it into remotePost.
  await page
    .getByLabel('Paste remote instance definition as json string')
    .fill(
      JSON.stringify({
        instance_name: 'pasted-remote',
        host: '10.9.8.7',
        port: 8443,
        token: 'paste-tok',
        fernet_key: 'fk-xyz',
        ssl_check: true,
      }),
    )

  // Values land on the Manual fields.
  await page.getByRole('tab', { name: 'Manual' }).click()
  await expect(page.getByLabel('Instance name')).toHaveValue('pasted-remote')
  await expect(page.getByLabel('Host')).toHaveValue('10.9.8.7')
  await expect(page.getByLabel('Token')).toHaveValue('paste-tok')

  const postReq = page.waitForRequest(
    (r) => /\/client\/remote-kaapana-instance/.test(r.url()) && r.method() === 'POST',
  )
  await page.getByRole('button', { name: 'submit' }).click()
  const body = (await postReq).postDataJSON()

  expect(body).toMatchObject({
    instance_name: 'pasted-remote',
    host: '10.9.8.7',
    port: 8443,
    token: 'paste-tok',
    fernet_key: 'fk-xyz',
    ssl_check: true,
  })

  await expect(page.getByText('Remote Instance', { exact: true })).toBeHidden()
  await expect(page.getByText('Instance name: pasted-remote')).toBeVisible()
})
