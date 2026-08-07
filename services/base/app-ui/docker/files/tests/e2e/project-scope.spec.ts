import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  defaultMockData,
  viewPathFor,
  UNSCOPED_VIEW_PATH,
  TASKS_PATH,
} from './fixtures/mock-backend'

// The four services base-ui's httpClient rewrites onto /project/<short_id>/
// (its PROJECT_SCOPED allowlist). Matched anywhere in the path so a call that
// bypasses the interceptor entirely is still caught.
const PROJECT_SCOPED_SERVICE = /(^|\/)(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

function row(page: import('@playwright/test').Page, name: string) {
  return page.locator('.v-list-item').filter({ hasText: name })
}

// The /project/<short_id> document prefix IS the project selection: API calls
// must be scoped to it (not to a default or any shared state), and a document
// without the prefix adopts the user's first project by redirecting onto it.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await installMockBackend(page)
  await seedShellState(page)
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const project = defaultMockData.projects[1]
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kube-helm-api/`),
  )
  // The view fetches /kube-helm-api/active-applications right after the
  // project resolves (onMounted), so booting alone triggers the scoped call.
  await page.goto(viewPathFor(project))
  await scoped
})

// The presence test above stays green while a NEW call goes out unscoped beside
// the scoped one, so this asserts the absence across boot and the interactions.
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

  // The view only renders apps belonging to the URL project, and the
  // interactions below need rows — so move the fixture's apps onto that project.
  await installMockBackend(page, {
    ...defaultMockData,
    activeApplications: defaultMockData.activeApplications.map((a) => ({
      ...a,
      project: project.id,
      paths: [`/applications/project/${project.id}/release/${a.release_name}`],
    })),
  })
  await seedShellState(page)
  // Barrier on the boot fetch itself, matched WITHOUT a prefix so it holds
  // whether or not the call is scoped; a DOM barrier can be satisfied before
  // the request goes out, and networkidle would be flaky under the 10s poll.
  const booted = page.waitForResponse((r) => /kube-helm-api\/active-applications/.test(r.url()))
  await page.goto(viewPathFor(project))
  await booted
  await expect(page.getByText('Applications requesting your input', { exact: true })).toBeVisible()

  // Neither dialog calls a backend today — covered so a status/log lookup added
  // later stays inside the window.
  await row(page, 'Broken Tool').getByRole('button', { name: 'Error' }).click()
  await expect(page.getByText('Problem starting the application')).toBeVisible()
  await page.getByRole('button', { name: 'Ok' }).click()
  await row(page, 'Volume Viewer').getByRole('button', { name: 'Starting...' }).click()
  await expect(page.getByText('Application is starting')).toBeVisible()
  await page.getByRole('button', { name: 'Back' }).click()
  await expect(page.locator('.v-overlay__scrim')).toHaveCount(0)

  // Finish interaction — the view's only write, and its only request outside
  // the boot and poll fetches.
  const finish = page.waitForResponse((r) => r.url().includes('/complete-active-application'))
  await row(page, 'Segmentation Editor').getByRole('button', { name: 'Finish Interaction' }).click()
  await page.getByRole('button', { name: 'Yes' }).click()
  await finish
  await expect(page.getByText('Segmentation Editor')).toHaveCount(0)

  expect(unscoped).toEqual([])
})

test('without a project prefix the view redirects onto the first project', async ({ page }) => {
  await installMockBackend(page)
  await seedShellState(page)
  await page.goto(UNSCOPED_VIEW_PATH)
  // "/" redirects to "/tasks", and the missing project prefix is filled in with
  // the user's first project -> the default Tasks route under /project/admin.
  await page.waitForURL(`**${TASKS_PATH}`)
  await expect(page.getByText('Applications requesting your input', { exact: true })).toBeVisible()
})
