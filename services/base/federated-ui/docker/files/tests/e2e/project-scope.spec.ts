import { test, expect } from '@playwright/test'
import { CLIENT, installMockBackend, secondProject, seedShellState, viewPathFor } from './fixtures/mock-backend'
import { card } from './fixtures/helpers'

const PROJECT_SCOPED_SERVICE = /(^|\/)(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${secondProject.short_id}/kaapana-backend/`),
  )
  await page.goto(viewPathFor(secondProject))
  await scoped
})

test('no request to a project-scoped service escapes the /project/<slug>/ prefix', async ({ page }) => {
  const prefix = `/project/${secondProject.short_id}/`
  const unscoped: string[] = []
  page.on('request', (r) => {
    const { pathname } = new URL(r.url())
    if (PROJECT_SCOPED_SERVICE.test(pathname) && !pathname.startsWith(prefix)) {
      unscoped.push(`${r.method()} ${pathname}`)
    }
  })

  await seedShellState(page)
  await installMockBackend(page)
  await page.clock.install()
  const listed = page.waitForResponse((r) => CLIENT.instances.test(r.url()))
  await page.goto(viewPathFor(secondProject))
  await listed
  const local = card(page, 'central-node')
  await expect(local).toBeVisible()

  const synced = page.waitForResponse((r) => CLIENT.sync.test(r.url()))
  await page.getByTestId('sync-remotes').click()
  await synced

  const datasets = page.waitForResponse((r) => CLIENT.datasets.test(r.url()))
  await local.getByRole('button', { name: 'Edit Allowed datasets' }).click()
  await datasets
  const saved = page.waitForResponse((r) => CLIENT.local.test(r.url()) && r.request().method() === 'PUT')
  await local.getByRole('button', { name: 'Save Allowed datasets' }).click()
  await saved

  const dags = page.waitForResponse((r) => CLIENT.dags.test(r.url()))
  await local.getByRole('button', { name: 'Edit Allowed workflows' }).click()
  await dags
  await local.getByRole('button', { name: 'Cancel editing Allowed workflows' }).click()

  const deleted = page.waitForResponse((r) => CLIENT.instance.test(r.url()) && r.request().method() === 'DELETE')
  await card(page, 'gpu-node-1').getByRole('button', { name: 'Delete gpu-node-1' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Delete instance' }).click()
  await deleted

  const polled = page.waitForResponse((r) => CLIENT.instances.test(r.url()))
  await page.clock.runFor(15_000)
  await polled

  expect(unscoped).toEqual([])
})
