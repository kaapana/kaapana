import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()
})

test('uninstalling an installed extension posts release name and version', async ({ page }) => {
  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-delete-chart') && r.method() === 'POST',
  )
  await page.getByRole('button', { name: 'Uninstall' }).click()

  expect((await reqPromise).postDataJSON()).toEqual({
    release_name: 'mitk-workbench-abc123',
    release_version: '1.0.0',
    helm_command_addons: '',
  })
})

test('force-uninstalling a stuck pending extension passes --no-hooks', async ({ page }) => {
  await page.getByRole('button', { name: 'Pending' }).click()

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-delete-chart') && r.method() === 'POST',
  )
  // exact: true so we hit the menu's button, not the outer Pending button whose
  // aggregated accessible name also contains "Force Uninstall".
  await page.getByRole('button', { name: 'Force Uninstall', exact: true }).click()

  expect((await reqPromise).postDataJSON()).toEqual({
    release_name: 'code-server-pending',
    release_version: '4.0.0',
    helm_command_addons: '--no-hooks',
  })
})
