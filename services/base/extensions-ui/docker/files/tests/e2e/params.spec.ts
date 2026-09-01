import { test, expect } from '@playwright/test'
import type { ExtensionMock, MockData } from './fixtures/mock-backend'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

// An extension whose backend reports extension_params as the literal string
// "null" (a real kube-helm response for param-less charts).
const nullParamExtension: ExtensionMock = {
  releaseName: 'null-params-app',
  name: 'null-params-app',
  chart_name: 'null-params-app',
  version: '1.0.0',
  versions: ['1.0.0'],
  available_versions: { '1.0.0': { deployments: [] } },
  multiinstallable: 'no',
  kind: 'application',
  experimental: 'no',
  resourceRequirement: 'cpu',
  successful: null,
  installed: 'no',
  description: 'Backend reports extension_params as the string "null"',
  display_name: 'Null Params App',
  keywords: ['kaapana-application'],
  extension_params: 'null',
}

const nullData: MockData = { ...defaultMockData, extensions: [nullParamExtension] }

test("string-'null' extension_params installs immediately with no config dialog", async ({
  page,
}) => {
  // Regression: getFormInfo used to call Object.keys('null') (-> ['0','1','2','3'])
  // and open a dialog the template refuses to render, so Install did nothing.
  await installMockBackend(page, nullData)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Null Params App')).toBeVisible()

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  await page.getByRole('button', { name: 'Install', exact: true }).click()

  await expect(page.getByRole('dialog')).toHaveCount(0)

  const payload = (await reqPromise).postDataJSON()
  expect(payload).toMatchObject({ name: 'null-params-app', version: '1.0.0' })
  expect(payload.extension_params).toBeUndefined()
})

test('a param-less install does not inherit the previous extension params', async ({ page }) => {
  // Regression: popUpExtension was never cleared, so after configuring a
  // parameterized extension, the next param-less install leaked the previous
  // extension's params into its /helm-install-chart payload.
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  // 1) Install the parameterized nnU-Net extension with a filled form.
  await page.getByRole('button', { name: 'Install', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('textbox', { name: /Workflow name/ }).fill('run-a')

  const firstReq = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  await dialog.getByRole('button', { name: 'Install', exact: true }).click()
  expect((await firstReq).postDataJSON().extension_params).toMatchObject({
    workflow_name: 'run-a',
  })

  // 2) Install the param-less JupyterLab extension right after.
  const secondReq = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  await page.getByRole('button', { name: 'Launch' }).click()

  const payload = (await secondReq).postDataJSON()
  expect(payload).toMatchObject({ name: 'jupyterlab', version: '3.2.0' })
  // nnU-Net's params must NOT ride along on JupyterLab's install.
  expect(payload.extension_params).toBeUndefined()
})
