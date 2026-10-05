import { test, expect } from '@playwright/test'
import {
  defaultMockData,
  installation,
  NNUNET_V1,
  PUBLIC_REPO,
  LAB_REPO,
  TOTALSEG,
  type MockData,
} from './fixtures/mock-backend'
import {
  API,
  card,
  cards,
  confirmAction,
  countRequests,
  dialog,
  failRoute,
  nextRequest,
  openFailureDetails,
  openView,
  toasts,
} from './fixtures/helpers'

const TOTALSEG_ID = 'eeeeeeee-0000-0000-0000-000000000001'

test('lists every extension with platform state in user terms', async ({ page }) => {
  await openView(page, 'extensions')

  await expect(cards(page)).toHaveCount(2)
  await expect(card(page, 'totalsegmentator')).toContainText('kaapana-public')
  await expect(card(page, 'totalsegmentator')).toContainText('Installed')
  await expect(card(page, 'totalsegmentator')).toContainText('2.0.0')
  await expect(card(page, 'radiomics')).toContainText('Installation failed')
  await expect(page.getByText('2 extensions on the platform')).toBeVisible()
})

test('the detail dialog shows the state of each installed item', async ({ page }) => {
  await openView(page, 'extensions')
  await card(page, 'radiomics').click()

  const details = dialog(page)
  await expect(details.getByTestId('status').first()).toContainText('Installation failed')
  await expect(details.getByRole('button', { name: /radiomics-workflow/ })).toContainText(
    'Installation failed',
  )
})

test('uninstall confirms what is removed, then reports that it started', async ({ page }) => {
  await openView(page, 'extensions')
  await card(page, 'totalsegmentator').click()
  await dialog(page).getByTestId('uninstall').click()

  const confirm = dialog(page)
  await expect(confirm).toContainText('Uninstall "totalsegmentator"?')
  await expect(confirm).toContainText('Version 2.0.0 from kaapana-public')
  await expect(confirm).toContainText('totalsegmentator-workflow')

  const request = nextRequest(page, `/extensions/${TOTALSEG_ID}/uninstall`, 'POST')
  await confirmAction(page, 'Uninstall extension')
  await request

  await expect(toasts(page).filter({ hasText: 'Uninstall started' })).toContainText(
    'totalsegmentator 2.0.0',
  )
  await expect(dialog(page).getByTestId('status').first()).toContainText('Uninstalling')
})

test('dismissing the confirmation uninstalls nothing', async ({ page }) => {
  await openView(page, 'extensions')
  const uninstalls = countRequests(page, `/extensions/${TOTALSEG_ID}/uninstall`, 'POST')
  await card(page, 'totalsegmentator').click()
  await dialog(page).getByTestId('uninstall').click()
  await dialog(page).getByRole('button', { name: 'Cancel' }).click()

  await expect(dialog(page).getByTestId('uninstall')).toBeEnabled()
  expect(uninstalls()).toBe(0)
})

test('uninstall is unavailable while an operation runs, and says why', async ({ page }) => {
  const data: MockData = {
    ...defaultMockData(),
    extensions: [
      installation(PUBLIC_REPO, NNUNET_V1, 'installing', 'eeeeeeee-0000-0000-0000-000000000003'),
    ],
  }
  await openView(page, 'extensions', data)
  await card(page, 'nnunet').click()

  await expect(dialog(page).getByTestId('uninstall')).toBeDisabled()
  await expect(dialog(page).getByTestId('uninstall-unavailable')).toContainText(
    'Uninstall becomes available once the current operation has finished.',
  )
})

test('an uninstalled extension shows no uninstall action', async ({ page }) => {
  const data: MockData = {
    ...defaultMockData(),
    extensions: [installation(PUBLIC_REPO, TOTALSEG, 'uninstalled', TOTALSEG_ID, 'uninstalled')],
  }
  await openView(page, 'extensions', data)
  await card(page, 'totalsegmentator').click()

  await expect(dialog(page).getByTestId('status').first()).toContainText('Uninstalled')
  await expect(dialog(page).getByTestId('uninstall')).toHaveCount(0)
})

test('running operations are polled until they settle, then polling stops', async ({ page }) => {
  const data: MockData = {
    ...defaultMockData(),
    extensions: [
      installation(PUBLIC_REPO, NNUNET_V1, 'pulling', 'eeeeeeee-0000-0000-0000-000000000003'),
    ],
  }
  const state = await openView(page, 'extensions', data)
  const lists = countRequests(page, API.extensions)
  await expect(card(page, 'nnunet')).toContainText('Downloading')

  state.extensions[0]!.status = 'installed'
  await expect(card(page, 'nnunet')).toContainText('Installed', { timeout: 10_000 })
  const settled = lists()
  await page.waitForTimeout(6_000)
  expect(lists()).toBe(settled)
})

test('settled extensions are not polled', async ({ page }) => {
  await openView(page, 'extensions')
  const lists = countRequests(page, API.extensions)
  await page.waitForTimeout(6_000)
  expect(lists()).toBe(0)
})

test('a rejected uninstall is reported with its details on demand', async ({ page }) => {
  await openView(page, 'extensions', defaultMockData(), {
    routes: (p) =>
      failRoute(
        p,
        `/extensions/${TOTALSEG_ID}/uninstall`,
        'the extension is already processed',
        409,
      ),
  })
  await card(page, 'totalsegmentator').click()
  await dialog(page).getByTestId('uninstall').click()
  await confirmAction(page, 'Uninstall extension')

  const details = await openFailureDetails(page, 'Uninstall failed to start')
  await expect(details).toContainText('409')
  await expect(details).toContainText('the extension is already processed')
})

test('nothing installed yet points to the catalog', async ({ page }) => {
  await openView(page, 'extensions', { ...defaultMockData(), extensions: [] }, { waitFor: 'empty' })

  const empty = page.getByTestId('empty-state')
  await expect(empty).toContainText('No extensions installed yet')
  await empty.getByRole('link', { name: 'Browse the catalog' }).click()
  await expect(page).toHaveURL(/\/catalog$/)
})

test('a failed load is an error, a failed refresh keeps the list with a warning', async ({
  page,
}) => {
  let fail = true
  await openView(page, 'extensions', defaultMockData(), {
    waitFor: 'empty',
    routes: (p) =>
      p.route(/\/extensions-api\/extensions$/, (route) =>
        fail
          ? route.fulfill({
              status: 500,
              contentType: 'application/json',
              body: JSON.stringify({ detail: 'boom' }),
            })
          : route.fallback(),
      ),
  })
  await expect(page.getByTestId('empty-state')).toContainText('Could not load the extensions')

  fail = false
  await page.getByTestId('empty-state').getByRole('button', { name: 'Try again' }).click()
  await expect(cards(page)).toHaveCount(2)

  fail = true
  await page.getByRole('button', { name: 'Refresh' }).click()
  await expect(page.getByTestId('stale-alert')).toContainText('last known state')
  await expect(cards(page)).toHaveCount(2)
  await page.getByTestId('stale-alert').getByRole('button', { name: 'Details' }).click()
  await expect(dialog(page)).toContainText('boom')
})

test('an unknown repository falls back to its id', async ({ page }) => {
  const data: MockData = { ...defaultMockData(), repositories: [PUBLIC_REPO] }
  await openView(page, 'extensions', data)

  await expect(card(page, 'radiomics')).toContainText(LAB_REPO.id)
})

test('an uninstalled extension disappears once the service drops its record', async ({ page }) => {
  const data: MockData = {
    ...defaultMockData(),
    extensions: [installation(PUBLIC_REPO, TOTALSEG, 'uninstalled', TOTALSEG_ID, 'uninstalled')],
  }
  const state = await openView(page, 'extensions', data)
  await expect(card(page, 'totalsegmentator')).toContainText('Uninstalled')

  state.extensions = []
  await expect(page.getByTestId('empty-state')).toContainText('No extensions installed yet', {
    timeout: 10_000,
  })
})
