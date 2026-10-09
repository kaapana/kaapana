import { test, expect, type Page } from '@playwright/test'
import { CLIENT, defaultMockData, localInstance } from './fixtures/mock-backend'
import {
  card,
  countRequests,
  dialog,
  dismissWithEscape,
  failRoute,
  nextRequest,
  openView,
  pressEscapeUntil,
  toasts,
} from './fixtures/helpers'

const onlyLocal = { ...defaultMockData, instances: [localInstance] }

async function openAddDialog(page: Page) {
  await page.getByTestId('add-remote').click()
  const add = dialog(page)
  await expect(add).toContainText('Add remote instance')
  return add
}

test('offers entering the details or pasting them', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)
  await expect(add.getByRole('tab', { name: 'Enter details' })).toBeVisible()
  await expect(add.getByRole('tab', { name: 'Paste details' })).toBeVisible()
})

test('an empty submit explains each missing field and sends nothing', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)
  const posts = countRequests(page, CLIENT.remote, 'POST')

  await add.getByRole('button', { name: 'Add instance' }).click()

  await expect(add.getByText('Enter the instance name of the remote platform')).toBeVisible()
  await expect(add.getByText('Enter the host name or IP address')).toBeVisible()
  await expect(add.getByText('Enter the token shown')).toBeVisible()
  await page.waitForTimeout(300)
  expect(posts()).toBe(0)
})

test('rejects a host with a protocol and an out-of-range port', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)

  await add.getByLabel('Host').fill('https://kaapana.example.org')
  await add.getByLabel('Port').fill('70000')
  await add.getByLabel('Token').click()

  await expect(add.getByText('Leave out the protocol')).toBeVisible()
  await expect(add.getByText('Enter a port number between 1 and 65535')).toBeVisible()
})

test('submitting from the paste tab still validates the entered details', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)
  const posts = countRequests(page, CLIENT.remote, 'POST')

  await add.getByRole('tab', { name: 'Paste details' }).click()
  await add.getByRole('button', { name: 'Add instance' }).click()

  await expect(add.getByText('Enter the instance name of the remote platform')).toBeVisible()
  await page.waitForTimeout(300)
  expect(posts()).toBe(0)
})

test('adds a remote instance from the entered details', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)

  await add.getByLabel('Instance name').fill('new-remote')
  await add.getByLabel('Host').fill('192.168.1.10')
  await add.getByLabel('Token').fill('tok-123')

  const post = nextRequest(page, CLIENT.remote, 'POST')
  await add.getByRole('button', { name: 'Add instance' }).click()
  expect((await post).postDataJSON()).toEqual({
    instance_name: 'new-remote',
    host: '192.168.1.10',
    port: 443,
    token: 'tok-123',
    fernet_key: 'deactivated',
    ssl_check: false,
  })

  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(toasts(page)).toContainText('Remote instance added')
  await expect(card(page, 'new-remote')).toBeVisible()
  await expect(page.getByTestId('add-remote')).toBeFocused()
})

test('pasted connection details fill the fields', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)

  await add.getByRole('tab', { name: 'Paste details' }).click()
  await add.getByLabel('Connection details').fill(
    JSON.stringify({
      instance_name: 'pasted-remote',
      host: '10.9.8.7',
      port: '8443',
      token: 'paste-tok',
      fernet_key: 'fk-xyz',
      ssl_check: true,
    }),
  )
  await expect(add.getByText('were filled from the pasted definition')).toBeVisible()

  await add.getByRole('tab', { name: 'Enter details' }).click()
  await expect(add.getByLabel('Instance name')).toHaveValue('pasted-remote')
  await expect(add.getByLabel('Port')).toHaveValue('8443')

  const post = nextRequest(page, CLIENT.remote, 'POST')
  await add.getByRole('button', { name: 'Add instance' }).click()
  expect((await post).postDataJSON()).toEqual({
    instance_name: 'pasted-remote',
    host: '10.9.8.7',
    port: 8443,
    token: 'paste-tok',
    fernet_key: 'fk-xyz',
    ssl_check: true,
  })
})

test('invalid pasted text is explained next to the field, not with a notification per keystroke', async ({
  page,
}) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)

  await add.getByRole('tab', { name: 'Paste details' }).click()
  await add.getByLabel('Connection details').pressSequentially('{"instance_')

  await expect(add.getByText('This is not a valid connection definition')).toBeVisible()
  await expect(page.locator('.vue-notification')).toHaveCount(0)
})

test('a rejected add keeps the dialog and explains the failure inline', async ({ page }) => {
  await openView(page, onlyLocal)
  await failRoute(page, CLIENT.remote, 'Kaapana instance already exists!', 400)
  const add = await openAddDialog(page)

  await add.getByLabel('Instance name').fill('gpu-node-1')
  await add.getByLabel('Host').fill('10.0.0.5')
  await add.getByLabel('Token').fill('tok')
  await add.getByRole('button', { name: 'Add instance' }).click()

  const alert = add.getByTestId('add-remote-error')
  await expect(alert).toContainText('Could not add gpu-node-1. Kaapana instance already exists!')
  await expect(add.getByLabel('Instance name')).toHaveValue('gpu-node-1')

  await alert.getByRole('button', { name: 'Details' }).click()
  await expect(dialog(page)).toContainText('400')
})

test('the add button is busy while the request runs, so it cannot be sent twice', async ({
  page,
}) => {
  await openView(page, onlyLocal)
  let release!: () => void
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route(CLIENT.remote, async (r) => {
    await held
    await r.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  const posts = countRequests(page, CLIENT.remote, 'POST')
  const add = await openAddDialog(page)

  await add.getByLabel('Instance name').fill('slow-remote')
  await add.getByLabel('Host').fill('10.1.1.1')
  await add.getByLabel('Token').fill('tok')
  const submit = add.getByRole('button', { name: 'Add instance' })
  await submit.click()
  await expect(submit).toBeDisabled()
  await submit.click({ force: true })
  release()

  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(posts()).toBe(1)
})

test('closing with entered details asks before discarding them', async ({ page }) => {
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)
  await add.getByLabel('Instance name').fill('half-done')

  await pressEscapeUntil(page, () => page.getByText('Discard the new remote instance?').isVisible())
  const confirm = dialog(page)
  await expect(confirm).toContainText('Discard the new remote instance?')
  await expect(confirm.getByRole('button', { name: 'Keep editing' })).toBeFocused()
  await confirm.getByRole('button', { name: 'Keep editing' }).click()
  await expect(page.getByLabel('Instance name')).toHaveValue('half-done')

  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  await dialog(page).getByRole('button', { name: 'Discard' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.getByTestId('add-remote').click()
  await expect(dialog(page).getByLabel('Instance name')).toHaveValue('')
})

test('closing an untouched dialog needs no confirmation', async ({ page }) => {
  await openView(page, onlyLocal)
  await openAddDialog(page)
  await dismissWithEscape(page)
})

test('reports unsaved details to the shell', async ({ page }) => {
  await page.addInitScript(() => {
    ;(window as any).__dirty = []
    window.parent.postMessage = ((message: any) => {
      if (message?.type === 'kaapana:view-dirty') (window as any).__dirty.push(message.dirty)
    }) as any
  })
  await openView(page, onlyLocal)
  const add = await openAddDialog(page)
  await add.getByLabel('Instance name').fill('x')
  await expect.poll(() => page.evaluate(() => (window as any).__dirty.at(-1))).toBe(true)

  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  await dialog(page).getByRole('button', { name: 'Discard' }).click()
  await expect.poll(() => page.evaluate(() => (window as any).__dirty.at(-1))).toBe(false)
})
