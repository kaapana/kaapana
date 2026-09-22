import { test, expect, type Page } from '@playwright/test'
import { countRequests, dialog, HELM, nextPost, openView, row } from './fixtures/helpers'

async function pickVersion(page: Page, name: string, version: string) {
  // v-select exposes a wrapper and an input, both role=combobox; open via the first.
  await row(page, name).getByRole('combobox').first().click()
  await page.getByRole('option', { name: version }).click()
}

test.describe('install and launch', () => {
  test.beforeEach(({ page }) => openView(page))

  test('installs a parameter-less extension and posts name/version/keywords', async ({ page }) => {
    const request = page.waitForRequest((r) => r.url().includes(HELM.install))
    // JupyterLab is multi-installable with no config form -> installs immediately.
    await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()

    const posted = await request
    expect(posted.postDataJSON()).toMatchObject({
      name: 'jupyterlab',
      version: '3.2.0',
      keywords: ['kaapana-application'],
    })
    // extension_params must be absent when the extension has no config form.
    expect(posted.postDataJSON().extension_params).toBeUndefined()
    // The interceptor must rewrite the call onto the project-scoped route.
    expect(posted.url()).toContain('/project/admin/kube-helm-api/helm-install-chart')
  })

  test('opens the config form and posts entered parameters', async ({ page }) => {
    // nnU-Net has a config form (string, bool, single-select).
    await row(page, 'nnU-Net Training').getByRole('button', { name: 'Install' }).click()
    await dialog(page).getByRole('textbox', { name: /Workflow name/ }).fill('my-training-run')

    const posted = nextPost(page, HELM.install)
    // Scope to the dialog: the Action-column button shares the "Install" label.
    await dialog(page).getByRole('button', { name: 'Install', exact: true }).click()

    const payload = await posted
    expect(payload).toMatchObject({ name: 'nnunet-workflow', version: '2.1.0' })
    expect(payload.extension_params).toEqual({
      workflow_name: 'my-training-run',
      enable_gpu: true,
      model_type: '3d_fullres',
    })
  })

  test('aborting the config form fires no install request', async ({ page }) => {
    const installs = countRequests(page, HELM.install)
    await row(page, 'nnU-Net Training').getByRole('button', { name: 'Install' }).click()

    await dialog(page).getByRole('button', { name: 'Abort' }).click()

    await expect(dialog(page)).toBeHidden()
    expect(installs()).toBe(0)
  })

  test('the selected version is reflected in the install payload', async ({ page }) => {
    await pickVersion(page, 'JupyterLab', '3.1.0')

    const posted = nextPost(page, HELM.install)
    await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()

    expect(await posted).toMatchObject({ name: 'jupyterlab', version: '3.1.0' })
  })
})

test('a version picked before a poll refresh survives into the install payload', async ({
  page,
}) => {
  // Regression: the 5s poll (Extensions.vue setInterval -> getHelmCharts) used to
  // replace the row array wholesale and reset the per-row version dropdown back
  // to the backend default, so a later Launch/Install posted the wrong version.
  await page.clock.install()
  await openView(page)
  await pickVersion(page, 'JupyterLab', '3.1.0')

  // Let a full poll cycle land (it refetches /extensions and rebuilds the rows).
  const polled = page.waitForResponse((r) => HELM.extensions.test(r.url()))
  await page.clock.runFor(5_000)
  await polled

  const posted = nextPost(page, HELM.install)
  await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()

  // The picked version, not the default 3.2.0, must survive the poll refresh.
  expect(await posted).toMatchObject({ name: 'jupyterlab', version: '3.1.0' })
})
