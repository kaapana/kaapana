import { test, expect } from '@playwright/test'
import { catalogue, dialog, extension, HELM, nextPost, openView, row } from './fixtures/helpers'

test("string-'null' extension_params installs immediately with no config dialog", async ({
  page,
}) => {
  // Regression: getFormInfo used to call Object.keys('null') (-> ['0','1','2','3'])
  // and open a dialog the template refuses to render, so Install did nothing.
  // The string is a real kube-helm response for param-less charts.
  await openView(
    page,
    catalogue([
      extension({ releaseName: 'null-params-app', display_name: 'Null Params App', extension_params: 'null' }),
    ]),
  )

  const posted = nextPost(page, HELM.install)
  await row(page, 'Null Params App').getByRole('button', { name: 'Install' }).click()

  await expect(dialog(page)).toHaveCount(0)
  const payload = await posted
  expect(payload).toMatchObject({ name: 'null-params-app', version: '1.0.0' })
  expect(payload.extension_params).toBeUndefined()
})

test('a param-less install does not inherit the previous extension params', async ({ page }) => {
  // Regression: popUpExtension was never cleared, so after configuring a
  // parameterized extension, the next param-less install leaked the previous
  // extension's params into its /helm-install-chart payload.
  await openView(page)

  // 1) Install the parameterized nnU-Net extension with a filled form.
  await row(page, 'nnU-Net Training').getByRole('button', { name: 'Install' }).click()
  await dialog(page).getByRole('textbox', { name: /Workflow name/ }).fill('run-a')
  const first = nextPost(page, HELM.install)
  await dialog(page).getByRole('button', { name: 'Install', exact: true }).click()
  expect((await first).extension_params).toMatchObject({ workflow_name: 'run-a' })

  // 2) Install the param-less JupyterLab extension right after.
  const second = nextPost(page, HELM.install)
  await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()

  const payload = await second
  expect(payload).toMatchObject({ name: 'jupyterlab', version: '3.2.0' })
  // nnU-Net's params must NOT ride along on JupyterLab's install.
  expect(payload.extension_params).toBeUndefined()
})
