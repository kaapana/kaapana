import { test, expect } from '@playwright/test'
import { CLIENT, defaultMockData, installMockBackend, localInstance, seedShellState, VIEW_PATH } from './fixtures/mock-backend'
import { card, collectPageErrors, countRequests, failRoute, field, openView, toasts } from './fixtures/helpers'

test('lists this platform and its remote instances in separate sections', async ({ page }) => {
  await openView(page)

  await expect(page.getByRole('heading', { level: 1, name: 'Instance overview' })).toBeVisible()
  await expect(page.getByTestId('summary')).toHaveText('This platform federates with 1 remote instance.')
  await expect(page.getByRole('heading', { name: 'This platform' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Remote instances' })).toBeVisible()

  const local = card(page, 'central-node')
  await expect(local).toContainText('This platform')
  await expect(field(local, 'Network')).toContainText('https://localhost:443')
  await expect(local.getByRole('button', { name: 'Copy connection details' })).toBeVisible()
  await expect(local.getByRole('button', { name: /^Delete/ })).toHaveCount(0)

  const remote = card(page, 'gpu-node-1')
  await expect(remote).toContainText('Remote instance')
  await expect(field(remote, 'Network')).toContainText('https://10.0.0.5:443')
  await expect(remote.getByRole('button', { name: 'Delete gpu-node-1' })).toBeVisible()
})

test('shows which fields each instance can edit', async ({ page }) => {
  await openView(page)

  const local = card(page, 'central-node')
  for (const label of ['Fernet key', 'Verify SSL', 'Sync automatically', 'Start workflows automatically', 'Allowed workflows', 'Allowed datasets']) {
    await expect(local.getByRole('button', { name: `Edit ${label}` })).toBeVisible()
  }
  for (const label of ['Network', 'Token']) {
    await expect(local.getByRole('button', { name: `Edit ${label}` })).toHaveCount(0)
  }

  const remote = card(page, 'gpu-node-1')
  for (const label of ['Network', 'Token', 'Fernet key', 'Verify SSL']) {
    await expect(remote.getByRole('button', { name: `Edit ${label}` })).toBeVisible()
  }
  for (const label of ['Sync automatically', 'Start workflows automatically', 'Allowed workflows', 'Allowed datasets']) {
    await expect(remote.getByRole('button', { name: `Edit ${label}` })).toHaveCount(0)
  }
})

test('states values in text, not only by colour', async ({ page }) => {
  await openView(page)

  const local = card(page, 'central-node')
  await expect(field(local, 'Verify SSL')).toContainText('Yes')
  await expect(field(local, 'Start workflows automatically')).toContainText('No')
  await expect(field(local, 'Fernet key')).toContainText('Deactivated')
  await expect(field(local, 'Allowed workflows')).toContainText('None')

  const remote = card(page, 'gpu-node-1')
  await expect(field(remote, 'Allowed workflows')).toContainText('dag-a')
  await expect(remote.getByTestId('freshness')).toContainText('Updated')
})

test('a remote instance that never reported shows that instead of a stale colour', async ({ page }) => {
  await openView(page, {
    ...defaultMockData,
    instances: [
      localInstance,
      { ...defaultMockData.instances[1], time_updated: '0001-01-01T00:00:00+00:00' },
    ],
  })

  const freshness = card(page, 'gpu-node-1').getByTestId('freshness')
  await expect(freshness).toHaveText('Never updated')
  await expect(freshness).not.toHaveClass(/text-error/)
  await expect(field(card(page, 'gpu-node-1'), 'Last updated')).toContainText('Never')
})

test('explains an empty remote list and offers to add one', async ({ page }) => {
  await openView(page, { ...defaultMockData, instances: [localInstance] })

  await expect(page.getByTestId('summary')).toHaveText(
    'This platform does not federate with any remote instance yet.',
  )
  const empty = page.getByTestId('no-remotes')
  await expect(empty).toContainText('No remote instances yet')
  await empty.getByRole('button', { name: 'Add remote instance' }).click()
  await expect(page.getByRole('dialog')).toContainText('Add remote instance')
})

test('sync is unavailable while there is nothing to sync', async ({ page }) => {
  await openView(page, { ...defaultMockData, instances: [localInstance] })
  await expect(page.getByTestId('sync-remotes')).toBeDisabled()
})

test('a failed first load shows a recoverable error instead of an empty list', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await failRoute(page, CLIENT.instances, 'database is down')
  await page.goto(VIEW_PATH)

  const error = page.getByTestId('load-error')
  await expect(error).toContainText('Could not load the instances')
  await expect(page.getByTestId('no-remotes')).toHaveCount(0)
  await expect(page.getByTestId('summary')).toHaveText('The instances could not be loaded.')

  await error.getByRole('button', { name: 'Details' }).click()
  const details = page.getByRole('dialog')
  await expect(details).toContainText('database is down')
  await expect(details).toContainText('500')
  await details.getByRole('button', { name: 'Close' }).click()

  await page.unroute(CLIENT.instances)
  await installMockBackend(page)
  await error.getByRole('button', { name: 'Try again' }).click()
  await expect(card(page, 'central-node')).toBeVisible()
  await expect(page.getByTestId('load-error')).toHaveCount(0)
})

test('a failed poll keeps the last list and says it may be outdated', async ({ page }) => {
  await page.clock.install()
  await openView(page)
  await expect(card(page, 'gpu-node-1')).toBeVisible()

  await failRoute(page, CLIENT.instances, 'timeout')
  const polled = page.waitForResponse((r) => CLIENT.instances.test(r.url()))
  await page.clock.runFor(15_000)
  await polled

  await expect(page.getByTestId('stale-list-alert')).toBeVisible()
  await expect(card(page, 'gpu-node-1')).toBeVisible()
})

test('sync remotes asks the backend for updates, confirms, and refetches', async ({ page }) => {
  await page.clock.install()
  await openView(page)
  const refetches = countRequests(page, CLIENT.instances)

  const synced = page.waitForResponse((r) => CLIENT.sync.test(r.url()))
  await page.getByTestId('sync-remotes').click()
  await synced

  await expect(toasts(page)).toContainText('Remote instances synced')
  await expect.poll(refetches).toBe(1)
})

test('a failed sync reports why, offers details, and skips the refetch', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await page.clock.install()
  await openView(page)
  await failRoute(page, CLIENT.sync, 'remote unreachable')
  const refetches = countRequests(page, CLIENT.instances)

  const synced = page.waitForResponse((r) => CLIENT.sync.test(r.url()))
  await page.getByTestId('sync-remotes').click()
  await synced

  const toast = toasts(page)
  await expect(toast).toContainText('Could not sync the remote instances')
  await expect(toast).toContainText('remote unreachable')
  await expect(toast).not.toContainText('Remote instances synced')
  expect(refetches()).toBe(0)

  await toast.getByText('Could not sync the remote instances').click()
  await expect(page.getByRole('dialog')).toContainText('GET')
  expect(pageErrors).toEqual([])
})

test('the list refreshes every 15 seconds', async ({ page }) => {
  await page.clock.install()
  await openView(page)
  const polls = countRequests(page, CLIENT.instances)
  await page.clock.runFor(30_000)
  await expect.poll(polls).toBe(2)
})
