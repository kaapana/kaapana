import { test, expect } from '@playwright/test'
import type { ExtensionMock, MockData } from './fixtures/mock-backend'
import {
  confirmAction,
  defaultMockData,
  installMockBackend,
  VIEW_PATH,
} from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()
})

test('uninstalling an installed extension posts release name and version', async ({ page }) => {
  // Uninstalling is destructive, so the row control opens a confirmation and
  // nothing is sent until it is accepted.
  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-delete-chart') && r.method() === 'POST',
  )
  await confirmAction(page, 'Uninstall extension')

  expect((await reqPromise).postDataJSON()).toEqual({
    release_name: 'mitk-workbench-abc123',
    release_version: '1.0.0',
    helm_command_addons: '',
  })
})

test('force-uninstalling a stuck pending extension passes --no-hooks', async ({ page }) => {
  await page.getByRole('button', { name: 'Pending' }).click()

  // exact: true so we hit the menu's button, not the outer Pending button whose
  // aggregated accessible name also contains "Force Uninstall".
  await page.getByRole('button', { name: 'Force Uninstall', exact: true }).click()

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-delete-chart') && r.method() === 'POST',
  )
  await confirmAction(page, 'Force uninstall extension')

  expect((await reqPromise).postDataJSON()).toEqual({
    release_name: 'code-server-pending',
    release_version: '4.0.0',
    helm_command_addons: '--no-hooks',
  })
})

// A multi-installable extension WITH a live deployment. defaultMockData has no
// such row (JupyterLab is multi-installable but not installed), so the whole
// "Delete instance" wording branch was otherwise never executed.
const installedMultiInstance: ExtensionMock = {
  releaseName: 'jupyterlab-inst-1',
  name: 'jupyterlab',
  chart_name: 'jupyterlab',
  version: '3.2.0',
  versions: ['3.2.0'],
  available_versions: {
    '3.2.0': {
      deployments: [
        {
          deployment_id: 'jupyterlab-inst-1',
          helm_status: 'deployed',
          kube_status: 'Running',
          links: [],
          ready: true,
        },
      ],
    },
  },
  multiinstallable: 'yes',
  kind: 'application',
  experimental: 'no',
  resourceRequirement: 'cpu',
  successful: 'yes',
  installed: 'yes',
  description: 'A launched notebook instance',
  display_name: 'JupyterLab Instance',
  keywords: ['kaapana-application'],
}

test('a multi-installable instance is deleted, not uninstalled, and says so', async ({ page }) => {
  const data: MockData = { ...defaultMockData, extensions: [installedMultiInstance] }
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('JupyterLab Instance')).toBeVisible()

  // Multi-installable rows say Delete, not Uninstall.
  await page.getByRole('button', { name: 'Delete', exact: true }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Delete "JupyterLab Instance"?')).toBeVisible()
  await expect(dialog.getByText('jupyterlab-inst-1')).toBeVisible()
  await expect(dialog.getByText(/Containers running for this instance are stopped/)).toBeVisible()

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-delete-chart') && r.method() === 'POST',
  )
  await confirmAction(page, 'Delete instance')

  expect((await reqPromise).postDataJSON()).toEqual({
    release_name: 'jupyterlab-inst-1',
    release_version: '3.2.0',
    helm_command_addons: '',
  })
})
