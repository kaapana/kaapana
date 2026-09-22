import { test, expect } from '@playwright/test'
import {
  catalogue,
  confirmAction,
  countRequests,
  deployed,
  dialog,
  dismissWithEscape,
  extension,
  HELM,
  nextPost,
  openView,
  row,
} from './fixtures/helpers'

// Removing a release is destructive, so every path here goes through a
// confirmation and nothing is sent until it is accepted.

test.describe('uninstall', () => {
  test.beforeEach(({ page }) => openView(page))

  test('posts the release name and version once confirmed', async ({ page }) => {
    await row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()

    const posted = nextPost(page, HELM.uninstall)
    await confirmAction(page, 'Uninstall extension')

    expect(await posted).toEqual({
      release_name: 'mitk-workbench-abc123',
      release_version: '1.0.0',
      helm_command_addons: '',
    })
  })

  test('dismissing the confirmation sends nothing and keeps the row as it was', async ({ page }) => {
    const uninstalls = countRequests(page, HELM.uninstall)
    const control = row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })
    await control.click()

    await dismissWithEscape(page)

    expect(uninstalls()).toBe(0)
    await expect(control).toBeVisible()
  })

  test('a stuck pending install can be force-uninstalled with --no-hooks', async ({ page }) => {
    await row(page, 'Code Server').getByRole('button', { name: 'Pending' }).click()
    // exact: the Pending button's aggregated name also contains the menu's label.
    await page.getByRole('button', { name: 'Force Uninstall', exact: true }).click()

    const posted = nextPost(page, HELM.uninstall)
    await confirmAction(page, 'Force uninstall extension')

    expect(await posted).toEqual({
      release_name: 'code-server-pending',
      release_version: '4.0.0',
      helm_command_addons: '--no-hooks',
    })
  })

  test('while it runs, the control shows progress and cannot be submitted twice', async ({
    page,
  }) => {
    let release!: () => void
    const held = new Promise<void>((resolve) => (release = resolve))
    const uninstalls = countRequests(page, HELM.uninstall)
    await page.route(`**${HELM.uninstall}`, async (r) => {
      await held
      await r.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    })

    const control = row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })
    await control.click()
    await confirmAction(page, 'Uninstall extension')

    await expect(control).toBeDisabled()
    await control.click({ force: true }).catch(() => {})
    expect(uninstalls()).toBe(1)

    release()
    await expect(control).toBeHidden()
  })
})

test('a multi-installable instance is deleted, not uninstalled, and the prompt says so', async ({
  page,
}) => {
  const instance = extension({
    releaseName: 'jupyterlab-inst-1',
    name: 'jupyterlab',
    display_name: 'JupyterLab Instance',
    version: '3.2.0',
    available_versions: { '3.2.0': deployed('jupyterlab-inst-1') },
    multiinstallable: 'yes',
    successful: 'yes',
    installed: 'yes',
  })
  await openView(page, catalogue([instance]))

  await row(page, 'JupyterLab Instance').getByRole('button', { name: 'Delete' }).click()
  await expect(dialog(page)).toContainText('Delete "JupyterLab Instance"?')
  await expect(dialog(page)).toContainText('jupyterlab-inst-1')
  await expect(dialog(page)).toContainText('Containers running for this instance are stopped')

  const posted = nextPost(page, HELM.uninstall)
  await confirmAction(page, 'Delete instance')

  expect(await posted).toMatchObject({ release_name: 'jupyterlab-inst-1', release_version: '3.2.0' })
})
