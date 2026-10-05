import { test, expect } from '@playwright/test'
import { CLIENT, defaultMockData, localInstance, remoteInstance } from './fixtures/mock-backend'
import {
  card,
  collectPageErrors,
  countRequests,
  dialog,
  failRoute,
  field,
  nextRequest,
  openView,
  toasts,
} from './fixtures/helpers'

const onlyRemote = { ...defaultMockData, instances: [remoteInstance] }
const onlyLocal = { ...defaultMockData, instances: [localInstance] }

test('edits a remote port and saves it to the remote endpoint', async ({ page }) => {
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await remote.getByLabel('Port').fill('8443')
  const put = nextRequest(page, CLIENT.remote, 'PUT')
  await remote.getByRole('button', { name: 'Save Network' }).click()

  expect((await put).postDataJSON()).toEqual({
    instance_name: 'gpu-node-1',
    host: '10.0.0.5',
    port: 8443,
    token: 'remote-token',
    fernet_key: 'abc123',
    ssl_check: false,
  })
  await expect(remote.getByLabel('Port')).toHaveCount(0)
  await expect(field(remote, 'Network')).toContainText('https://10.0.0.5:8443')
  await expect(toasts(page)).toContainText('Network saved')
})

test('Enter in an edited field saves it', async ({ page }) => {
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Token' }).click()
  await remote.getByRole('textbox', { name: 'Token' }).fill('new-token')
  const put = nextRequest(page, CLIENT.remote, 'PUT')
  await remote.getByRole('textbox', { name: 'Token' }).press('Enter')
  expect((await put).postDataJSON().token).toBe('new-token')
})

test('an invalid value cannot be saved and says how to fix it', async ({ page }) => {
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await remote.getByLabel('Port').fill('0')
  await expect(remote.getByText('Enter a port number between 1 and 65535')).toBeVisible()
  await expect(remote.getByRole('button', { name: 'Save Network' })).toBeDisabled()
})

test('cancel discards the edit without a request', async ({ page }) => {
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')
  const puts = countRequests(page, CLIENT.remote, 'PUT')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await remote.getByLabel('Port').fill('9999')
  await remote.getByRole('button', { name: 'Cancel editing Network' }).click()

  await expect(field(remote, 'Network')).toContainText('https://10.0.0.5:443')
  expect(puts()).toBe(0)
})

test('only one field is edited at a time', async ({ page }) => {
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await expect(remote.getByRole('button', { name: 'Edit Token' })).toBeDisabled()
  await expect(remote.getByRole('button', { name: 'Delete gpu-node-1' })).toBeDisabled()
})

test('edits a local setting and saves it to the client endpoint', async ({ page }) => {
  await openView(page, onlyLocal)
  const local = card(page, 'central-node')

  await local.getByRole('button', { name: 'Edit Sync automatically' }).click()
  await local.getByLabel('Check remote instances for updates automatically').click()
  const put = nextRequest(page, CLIENT.local, 'PUT')
  await local.getByRole('button', { name: 'Save Sync automatically' }).click()

  expect((await put).postDataJSON()).toEqual({
    ssl_check: true,
    fernet_encrypted: false,
    automatic_update: false,
    automatic_workflow_execution: false,
    allowed_dags: [],
    allowed_datasets: [],
  })
  await expect(field(local, 'Sync automatically')).toContainText('No')
})

test('a background poll mid-edit does not discard the unsaved value', async ({ page }) => {
  await page.clock.install()
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await remote.getByLabel('Port').fill('8443')

  const polled = page.waitForResponse((r) => CLIENT.instances.test(r.url()))
  await page.clock.runFor(15_000)
  await polled

  const put = nextRequest(page, CLIENT.remote, 'PUT')
  await remote.getByRole('button', { name: 'Save Network' }).click()
  expect((await put).postDataJSON().port).toBe(8443)
})

test('a failed save keeps the field open with the entered value and offers details', async ({
  page,
}) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, onlyRemote)
  await failRoute(page, CLIENT.remote, 'instance is unreachable')
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await remote.getByLabel('Port').fill('8443')
  await remote.getByRole('button', { name: 'Save Network' }).click()

  await expect(toasts(page)).toContainText('Could not save the change')
  await expect(remote.getByLabel('Port')).toHaveValue('8443')

  await toasts(page).getByText('Could not save the change').click()
  await expect(dialog(page)).toContainText('PUT')
  await expect(dialog(page)).toContainText('instance is unreachable')
  expect(pageErrors).toEqual([])
})

test('workflow options load only when their editor opens', async ({ page }) => {
  await openView(page, onlyLocal)
  const local = card(page, 'central-node')
  const dagLoads = countRequests(page, CLIENT.dags)

  await page.waitForTimeout(300)
  expect(dagLoads()).toBe(0)

  await local.getByRole('button', { name: 'Edit Allowed workflows' }).click()
  await local.getByRole('combobox', { name: 'Allowed workflows' }).click()
  await page.getByRole('option', { name: 'dag-b' }).click()
  await page.keyboard.press('Escape')
  const put = nextRequest(page, CLIENT.local, 'PUT')
  await local.getByRole('button', { name: 'Save Allowed workflows' }).click()

  expect((await put).postDataJSON().allowed_dags).toEqual(['dag-b'])
  expect(dagLoads()).toBe(1)
  await expect(field(local, 'Allowed workflows')).toContainText('dag-b')
})

test('dataset options are limited to project datasets', async ({ page }) => {
  await openView(page, onlyLocal)
  const local = card(page, 'central-node')

  const loaded = nextRequest(page, CLIENT.datasets, 'GET')
  await local.getByRole('button', { name: 'Edit Allowed datasets' }).click()
  expect(new URL((await loaded).url()).searchParams.get('skip_identifiers')).toBe('true')

  await local.getByRole('combobox', { name: 'Allowed datasets' }).click()
  await expect(page.getByRole('option', { name: 'ds-project' })).toBeVisible()
  await expect(page.getByRole('option', { name: 'ds-private' })).toHaveCount(0)
})

test('a failed dataset load reports it and keeps the editor usable', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, onlyLocal)
  await failRoute(page, CLIENT.datasets, 'datasets are down')
  const local = card(page, 'central-node')

  await local.getByRole('button', { name: 'Edit Allowed datasets' }).click()
  await expect(toasts(page)).toContainText('Could not load the datasets')
  await expect(local.getByRole('button', { name: 'Save Allowed datasets' })).toBeEnabled()

  await toasts(page).getByText('Could not load the datasets').click()
  await expect(dialog(page)).toContainText('datasets are down')
  expect(pageErrors).toEqual([])
})

test('deleting a remote instance asks first and says what follows', async ({ page }) => {
  await openView(page, onlyRemote)
  await card(page, 'gpu-node-1').getByRole('button', { name: 'Delete gpu-node-1' }).click()

  const confirm = dialog(page)
  await expect(confirm).toContainText('Delete remote instance “gpu-node-1”?')
  await expect(confirm).toContainText(
    'deletes the jobs it sent to that instance and the workflows received from it',
  )
  await expect(confirm).toContainText('Your datasets and your own workflows are kept')
  await expect(confirm).toContainText('The remote platform itself is not changed')

  const del = nextRequest(page, CLIENT.instance, 'DELETE')
  await confirm.getByRole('button', { name: 'Delete instance' }).click()
  expect((await del).url()).toContain('kaapana_instance_id=2')

  await expect(card(page, 'gpu-node-1')).toHaveCount(0)
  await expect(toasts(page)).toContainText('Remote instance deleted')
  await expect(page.getByTestId('no-remotes')).toBeVisible()
})

test('cancelling the delete confirmation sends nothing', async ({ page }) => {
  await openView(page, onlyRemote)
  const deletes = countRequests(page, CLIENT.instance, 'DELETE')
  await card(page, 'gpu-node-1').getByRole('button', { name: 'Delete gpu-node-1' }).click()
  await dialog(page).getByRole('button', { name: 'Cancel' }).click()

  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(card(page, 'gpu-node-1')).toBeVisible()
  expect(deletes()).toBe(0)
})

test('a failed delete keeps the instance and reports why', async ({ page }) => {
  await openView(page, onlyRemote)
  await failRoute(page, CLIENT.instance, 'Kaapana instance not found', 404)
  await card(page, 'gpu-node-1').getByRole('button', { name: 'Delete gpu-node-1' }).click()
  await dialog(page).getByRole('button', { name: 'Delete instance' }).click()

  await expect(toasts(page)).toContainText('Could not delete the remote instance')
  await expect(card(page, 'gpu-node-1')).toBeVisible()

  await toasts(page).getByText('Could not delete the remote instance').click()
  await expect(dialog(page)).toContainText('Kaapana instance not found')
})

test('copies the connection details of this platform in the shape the paste tab reads', async ({
  page,
  context,
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await openView(page, onlyLocal)

  await card(page, 'central-node').getByRole('button', { name: 'Copy connection details' }).click()
  await expect(toasts(page)).toContainText('Connection details copied')

  const copied = JSON.parse(await page.evaluate(() => navigator.clipboard.readText()))
  expect(copied).toEqual({
    instance_name: 'central-node',
    host: 'localhost',
    port: 443,
    token: 'local-token',
    fernet_key: 'deactivated',
    ssl_check: true,
  })
})

test('an edited field is reported to the shell as unsaved work', async ({ page }) => {
  await page.addInitScript(() => {
    ;(window as any).__dirty = []
    window.parent.postMessage = ((message: any) => {
      if (message?.type === 'kaapana:view-dirty') (window as any).__dirty.push(message.dirty)
    }) as any
  })
  await openView(page, onlyRemote)
  const remote = card(page, 'gpu-node-1')

  await remote.getByRole('button', { name: 'Edit Network' }).click()
  await remote.getByLabel('Port').fill('8443')
  await expect.poll(() => page.evaluate(() => (window as any).__dirty.at(-1))).toBe(true)

  await remote.getByRole('button', { name: 'Cancel editing Network' }).click()
  await expect.poll(() => page.evaluate(() => (window as any).__dirty.at(-1))).toBe(false)
})
