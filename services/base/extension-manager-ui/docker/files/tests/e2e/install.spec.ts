import { test, expect } from '@playwright/test'
import {
  defaultMockData,
  installation,
  LAB_REPO,
  manifestResponse,
  NNUNET_V1,
  NNUNET_V11,
  PUBLIC_REPO,
} from './fixtures/mock-backend'
import {
  API,
  card,
  countRequests,
  dialog,
  failRoute,
  nextRequest,
  openFailureDetails,
  openView,
  toasts,
} from './fixtures/helpers'

async function selectVersion(page: import('@playwright/test').Page, version: string) {
  await dialog(page).locator('div[role="combobox"]', { hasText: 'Version' }).click()
  await page.getByRole('option', { name: version, exact: true }).click()
}

test('installs the selected version and reports that it started', async ({ page }) => {
  await openView(page)
  await card(page, 'nnunet').click()
  await selectVersion(page, '1.0.0')

  const request = nextRequest(page, API.install, 'POST')
  await dialog(page).getByTestId('install').click()
  const params = new URL((await request).url()).searchParams

  expect(params.get('repository_id')).toBe(PUBLIC_REPO.id)
  expect(params.get('tag')).toBe('aaaaaaaa-0000-0000-0000-000000000001-v1.0.0')
  await expect(toasts(page).filter({ hasText: 'Installation started' })).toContainText(
    'nnunet 1.0.0',
  )
  await expect(dialog(page).getByTestId('install')).toBeDisabled()
  await expect(dialog(page).getByTestId('install-state')).toContainText('Waiting to install')
})

test('an installed version cannot be installed again and says why', async ({ page }) => {
  await openView(page)
  await card(page, 'totalsegmentator').click()

  await expect(dialog(page).getByTestId('install')).toBeDisabled()
  await expect(dialog(page).getByTestId('install-state')).toContainText('Installed')
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'This version is already installed. Manage it on the Extensions page.',
  )
})

test('a failed installation offers a retry', async ({ page }) => {
  await openView(page)
  await card(page, 'radiomics').click()

  const retry = dialog(page).getByTestId('install')
  await expect(retry).toHaveText('Retry installation')
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'The last installation of this version failed.',
  )

  const request = nextRequest(page, API.install, 'POST')
  await retry.click()
  expect(new URL((await request).url()).searchParams.get('repository_id')).toBe(LAB_REPO.id)
})

test('the install cannot be submitted twice while it runs', async ({ page }) => {
  let release: () => void = () => {}
  const held = new Promise<void>((resolve) => (release = resolve))
  await openView(page, 'catalog', defaultMockData(), {
    routes: (p) =>
      p.route(/\/extensions\/install\?/, async (route) => {
        await held
        await route.fallback()
      }),
  })
  const installs = countRequests(page, API.install, 'POST')
  await card(page, 'nnunet').click()

  const install = dialog(page).getByTestId('install')
  await install.click()
  await expect(install).toBeDisabled()
  await install.click({ force: true })
  release()

  await expect(toasts(page).filter({ hasText: 'Installation started' })).toBeVisible()
  expect(installs()).toBe(1)
})

test('the catalog follows a running installation until it settles', async ({ page }) => {
  const data = await openView(page)
  await card(page, 'nnunet').click()
  await dialog(page).getByTestId('install').click()
  await expect(dialog(page).getByTestId('install-state')).toContainText('Waiting to install')

  const created = data.extensions.find((extension) => extension.manifest.name === 'nnunet')!
  created.status = 'installed'

  await expect(dialog(page).getByTestId('install-state')).toContainText('Installed', {
    timeout: 10_000,
  })
})

test('a rejected install is reported with its details on demand', async ({ page }) => {
  await openView(page, 'catalog', defaultMockData(), {
    routes: (p) =>
      failRoute(p, /\/extensions\/install\?/, 'No installer found for content type task-v1', 400),
  })
  await card(page, 'nnunet').click()
  await dialog(page).getByTestId('install').click()

  const details = await openFailureDetails(page, 'Installation failed to start')
  await expect(details).toContainText('Could not start installing nnunet 1.1.0.')
  await expect(details).toContainText('400')
  await expect(details).toContainText('No installer found for content type task-v1')
  await expect(details).toContainText('POST /extensions-api/extensions/install')
})

test('a just-uninstalled version becomes installable once its record is gone', async ({ page }) => {
  const data = defaultMockData()
  data.extensions[0]!.status = 'uninstalled'
  const state = await openView(page, 'catalog', data)
  await card(page, 'totalsegmentator').click()

  await expect(dialog(page).getByTestId('install')).toBeDisabled()
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'It can be installed again in a moment.',
  )

  state.extensions = state.extensions.slice(1)
  await expect(dialog(page).getByTestId('install')).toBeEnabled({ timeout: 10_000 })
})

function withNnunetInstalled(version = NNUNET_V1, status = 'installed') {
  const data = defaultMockData()
  data.extensions.push(
    installation(PUBLIC_REPO, version, status, 'eeeeeeee-0000-0000-0000-000000000010'),
  )
  return data
}

test('a newer version of an installed extension is offered as an update', async ({ page }) => {
  await openView(page, 'catalog', withNnunetInstalled())
  await card(page, 'nnunet').click()

  const update = dialog(page).getByTestId('install')
  await expect(update).toHaveText('Update to 1.1.0')
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'Version 1.0.0 is installed.',
  )

  const request = nextRequest(page, API.install, 'POST')
  await update.click()
  expect(new URL((await request).url()).searchParams.get('tag')).toBe(
    'aaaaaaaa-0000-0000-0000-000000000001-v1.1.0',
  )
  await expect(toasts(page).filter({ hasText: 'Update started' })).toContainText(
    'nnunet is being updated to 1.1.0',
  )
  await expect(dialog(page).getByTestId('install-state')).toContainText('Updating')
})

test('a failed update offers a retry of the same version', async ({ page }) => {
  const data = withNnunetInstalled(NNUNET_V1, 'update_failed')
  data.extensions.at(-1)!.pending_update = manifestResponse(PUBLIC_REPO, NNUNET_V11)
  await openView(page, 'catalog', data)
  await card(page, 'nnunet').click()

  await expect(dialog(page).getByTestId('install')).toHaveText('Retry update')
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'The update to this version failed. Version 1.0.0 is still installed.',
  )
})

test('an older version cannot be installed over a newer one', async ({ page }) => {
  await openView(page, 'catalog', withNnunetInstalled(NNUNET_V11))
  await card(page, 'nnunet').click()
  await selectVersion(page, '1.0.0')

  await expect(dialog(page).getByTestId('install')).toBeDisabled()
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'Version 1.1.0 is installed. Downgrades are not supported.',
  )
})

test('a version from another repository cannot update the installed extension', async ({
  page,
}) => {
  const data = withNnunetInstalled()
  data.manifests[LAB_REPO.id]!.push(manifestResponse(LAB_REPO, NNUNET_V11))
  await openView(page, 'catalog', data)
  await card(page, 'nnunet').filter({ hasText: 'lab-internal' }).click()

  await expect(dialog(page).getByTestId('install')).toBeDisabled()
  await expect(dialog(page).getByTestId('install-state')).toContainText(
    'Version 1.0.0 is installed from another repository.',
  )
})
