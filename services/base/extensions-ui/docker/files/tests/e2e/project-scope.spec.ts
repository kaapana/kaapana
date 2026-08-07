import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  defaultMockData,
  viewPathFor,
  UNSCOPED_VIEW_PATH,
  VIEW_PATH,
} from './fixtures/mock-backend'

// The four services base-ui's httpClient rewrites onto /project/<short_id>/
// (its PROJECT_SCOPED allowlist). Matched anywhere in the path so a call that
// bypasses the interceptor entirely is still caught.
const PROJECT_SCOPED_SERVICE = /(^|\/)(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

// The /project/<short_id> document prefix IS the project selection: API calls
// must be scoped to it (not to a default or any shared state), and a document
// without the prefix adopts the user's first project by redirecting onto it.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await installMockBackend(page)
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const project = defaultMockData.projects[1]
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kube-helm-api/`),
  )
  await page.goto(viewPathFor(project))
  await scoped
})

// The presence test above stays green while a NEW call goes out unscoped beside
// the scoped one — Upload.vue's FilePond endpoint skips httpClient and is
// exactly that shape — so this asserts the absence across boot and interactions.
test('no request to a project-scoped service escapes the /project/<slug>/ prefix', async ({
  page,
}) => {
  const project = defaultMockData.projects[1]
  const prefix = `/project/${project.short_id}/`
  const unscoped: string[] = []
  page.on('request', (r) => {
    const { pathname } = new URL(r.url())
    if (PROJECT_SCOPED_SERVICE.test(pathname) && !pathname.startsWith(prefix)) {
      unscoped.push(`${r.method()} ${pathname}`)
    }
  })

  await installMockBackend(page)
  // Barrier on the boot RESPONSE, matched without a prefix so it holds whether
  // or not the call is scoped; a DOM barrier can be satisfied before the
  // request even goes out.
  const listed = page.waitForResponse((r) => /\/kube-helm-api\/extensions(\?.*)?$/.test(r.url()))
  await page.goto(viewPathFor(project))
  await listed
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  // Refresh the marketplace (the only header action that calls the backend).
  const refreshed = page.waitForResponse((r) => r.url().includes('/kube-helm-api/update-extensions'))
  await page.getByTestId('update-extensions').click()
  await refreshed

  // Install: the one action whose URL the interceptor rewrites on a POST.
  const installed = page.waitForResponse((r) => r.url().includes('/kube-helm-api/helm-install-chart'))
  await page.getByRole('button', { name: 'Launch' }).first().click()
  await installed

  // Uninstall, the mirror-image call.
  const uninstalled = page.waitForResponse((r) => r.url().includes('/kube-helm-api/helm-delete-chart'))
  await page.getByRole('button', { name: 'Uninstall' }).first().click()
  await uninstalled

  // The motivating call: FilePond never touches httpClient, so Upload.vue
  // prepends getProjectBase() by hand. Only a real file drop exercises it —
  // setOptions merely CONFIGURES the endpoint.
  const uploaded = page.waitForResponse((r) => r.url().includes('/kube-helm-api/filepond-upload'))
  await page.locator('input.filepond--browser').setInputFiles({
    name: 'chart.tgz',
    mimeType: 'application/gzip',
    buffer: Buffer.from('mock chart'),
  })
  await uploaded

  expect(unscoped).toEqual([])
})

test('without a project prefix the view redirects onto the first project', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(UNSCOPED_VIEW_PATH)
  await page.waitForURL(`**${VIEW_PATH}`)
  await expect(page.getByText('MITK Workbench')).toBeVisible()
})
