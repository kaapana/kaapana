import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()
})

test('installs a parameter-less extension and posts name/version/keywords', async ({ page }) => {
  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  // JupyterLab is multi-installable with no config form -> installs immediately.
  await page.getByRole('button', { name: 'Launch' }).click()

  const req = await reqPromise
  expect(req.postDataJSON()).toMatchObject({
    name: 'jupyterlab',
    version: '3.2.0',
    keywords: ['kaapana-application'],
  })
  // extension_params must be absent when the extension has no config form.
  expect(req.postDataJSON().extension_params).toBeUndefined()

  // The interceptor must rewrite the call onto the project-scoped route.
  expect(req.url()).toContain('/project/admin/kube-helm-api/helm-install-chart')
})

test('opens the config form and posts entered parameters', async ({ page }) => {
  // nnU-Net has a config form (string, bool, single-select).
  // exact: true so "Install" does not also match the "Uninstall" button.
  await page.getByRole('button', { name: 'Install', exact: true }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('textbox', { name: /Workflow name/ }).fill('my-training-run')

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  // Scope to the dialog: the Action-column button shares the "Install" label.
  await dialog.getByRole('button', { name: 'Install', exact: true }).click()

  const payload = (await reqPromise).postDataJSON()
  expect(payload).toMatchObject({ name: 'nnunet-workflow', version: '2.1.0' })
  expect(payload.extension_params).toEqual({
    workflow_name: 'my-training-run',
    enable_gpu: true,
    model_type: '3d_fullres',
  })
})

test('cancelling the config form fires no install request', async ({ page }) => {
  let installCalls = 0
  page.on('request', (r) => {
    if (r.url().includes('/kube-helm-api/helm-install-chart')) installCalls++
  })

  await page.getByRole('button', { name: 'Install', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  // "Cancel" per the guidelines: dismissing a form destroys nothing, so it is a
  // secondary action, not the error-coloured "Abort" it used to be.
  await dialog.getByRole('button', { name: 'Cancel' }).click()

  await expect(dialog).toBeHidden()
  await page.waitForTimeout(500)
  expect(installCalls).toBe(0)
})

test('the selected version is reflected in the install payload', async ({ page }) => {
  const row = page.getByRole('row', { name: /JupyterLab/ })
  // v-select exposes both a wrapper and an input with role=combobox; open via the first.
  await row.getByRole('combobox').first().click()
  await page.getByRole('option', { name: '3.1.0' }).click()

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  await row.getByRole('button', { name: 'Launch' }).click()

  expect((await reqPromise).postDataJSON()).toMatchObject({
    name: 'jupyterlab',
    version: '3.1.0',
  })
})

test('a version picked before a poll refresh survives into the install payload', async ({
  page,
}) => {
  // Regression: the 5s poll (Extensions.vue setInterval -> getHelmCharts) used to
  // replace the row array wholesale and reset the per-row version dropdown back
  // to the backend default, so a later Launch/Install posted the wrong version.
  const row = page.getByRole('row', { name: /JupyterLab/ })
  await row.getByRole('combobox').first().click()
  await page.getByRole('option', { name: '3.1.0' }).click()

  // Let a full poll cycle land (it refetches /extensions and rebuilds the rows).
  await page.waitForResponse(
    (r) => /\/kube-helm-api\/extensions(\?.*)?$/.test(r.url()),
    { timeout: 15000 },
  )
  // Give Vue a tick to re-render the refreshed rows before acting on them.
  await page.waitForTimeout(500)

  const reqPromise = page.waitForRequest(
    (r) => r.url().includes('/kube-helm-api/helm-install-chart') && r.method() === 'POST',
  )
  await row.getByRole('button', { name: 'Launch' }).click()

  // The picked version, not the default 3.2.0, must survive the poll refresh.
  expect((await reqPromise).postDataJSON()).toMatchObject({
    name: 'jupyterlab',
    version: '3.1.0',
  })
})
