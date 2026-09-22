import { test, expect } from '@playwright/test'
import { HELM, nextPost, openView, row } from './fixtures/helpers'

test.beforeEach(({ page }) => openView(page))

test('uninstalling an installed extension posts release name and version', async ({ page }) => {
  const posted = nextPost(page, HELM.uninstall)
  await row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()

  expect(await posted).toEqual({
    release_name: 'mitk-workbench-abc123',
    release_version: '1.0.0',
    helm_command_addons: '',
  })
})

test('force-uninstalling a stuck pending extension passes --no-hooks', async ({ page }) => {
  await row(page, 'Code Server').getByRole('button', { name: 'Pending' }).click()

  const posted = nextPost(page, HELM.uninstall)
  // exact: true so we hit the menu's button, not the outer Pending button whose
  // aggregated accessible name also contains "Force Uninstall".
  await page.getByRole('button', { name: 'Force Uninstall', exact: true }).click()

  expect(await posted).toEqual({
    release_name: 'code-server-pending',
    release_version: '4.0.0',
    helm_command_addons: '--no-hooks',
  })
})
