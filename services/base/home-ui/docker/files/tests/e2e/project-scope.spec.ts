import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  defaultMockData,
  defaultProject,
  viewPathFor,
  UNSCOPED_VIEW_PATH,
  VIEW_PATH,
} from './fixtures/mock-backend'

// The four services base-ui's httpClient rewrites onto /project/<short_id>/
// (its PROJECT_SCOPED allowlist). Matched anywhere in the path so a call that
// bypasses the interceptor entirely is still caught.
const PROJECT_SCOPED_SERVICE = /(^|\/)(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

// The /project/<short_id> document prefix IS the project selection: API calls
// must be scoped to it and the project store must resolve the same slug, not
// fall back to a default or shared state.

test('API calls and the project store follow the project in the document URL', async ({ page }) => {
  await installMockBackend(page)
  await seedShellState(page)
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const project = defaultMockData.projects[1]
  // Deliberately a request whose prefix can only come from the interceptor:
  // the project list writes /project/<short_id> into the dashboard path itself,
  // so asserting on that one would pass with the interceptor removed.
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kaapana-backend/monitoring/query/`),
  )
  await page.goto(viewPathFor(project))
  await scoped
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  await expect(page.getByText('You are working in project')).toContainText(project.name)
})

// The presence test above stays green while a NEW call goes out unscoped beside
// the scoped one, so this asserts the absence. The invariant is "SOME known
// /project/<slug>/ prefix", not the document's: ProjectStatsCard deliberately
// fans out per-project dashboard calls with foreign prefixes.
test('no request to a project-scoped service escapes the /project/<slug>/ prefix', async ({
  page,
}) => {
  const project = defaultMockData.projects[1]
  const known = defaultMockData.projects.map((p) => String(p.short_id ?? p.id))
  const unscoped: string[] = []
  page.on('request', (r) => {
    const { pathname } = new URL(r.url())
    if (!PROJECT_SCOPED_SERVICE.test(pathname)) return
    const slug = /^\/project\/([^/]+)\//.exec(pathname)?.[1]
    if (!slug || !known.includes(slug)) unscoped.push(`${r.method()} ${pathname}`)
  })

  await installMockBackend(page)
  await seedShellState(page)
  // Fake clock so the 15s polls land inside the collection window (see the
  // closing runFor) instead of after the test.
  await page.clock.install()
  // Barriers on RESPONSES, matched without a prefix so they hold whether or not
  // the call is scoped; a DOM barrier can be satisfied before the request goes
  // out, and networkidle would be flaky under the 15s polls.
  const metric = page.waitForResponse((r) =>
    /\/kaapana-backend\/monitoring\/query\//.test(r.url()),
  )
  const badge = page.waitForResponse((r) =>
    r.url().includes('/kube-helm-api/pending-applications-count'),
  )
  const fanOut = page.waitForResponse((r) =>
    r.url().includes(`/project/${project.short_id}/kaapana-backend/dataset/dashboard`),
  )
  await page.goto(viewPathFor(project))
  await Promise.all([metric, badge, fanOut])
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  await expect(page.getByText('You are working in project')).toContainText(project.name)

  // The detail dialog re-queries the dashboard with the histogram fields, the
  // one project-scoped call the boot fetches never make.
  const detail = page.waitForResponse(
    (r) =>
      r.url().includes('/kaapana-backend/dataset/dashboard') &&
      r.request().method() === 'POST' &&
      r.request().postDataJSON().names.length > 0,
  )
  await page.getByRole('button', { name: 'Details' }).click()
  await detail
  await expect(page.locator('.v-dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('.v-dialog')).toBeHidden()

  // Notification write path: not allowlisted today, covered in case it grows a
  // scoped call.
  await page.locator('.v-card').filter({ hasText: 'Notifications' }).getByText('Workflow finished').click()
  const read = page.waitForResponse((r) => r.url().includes('/notifications/v2/n-1/read'))
  await page.locator('.v-dialog').getByRole('button', { name: 'Mark as read' }).click()
  await read
  await expect(page.getByText("No notifications — you're all caught up")).toBeVisible()

  // One tick of the 15s polls. Load-bearing: with the clock faked this advance
  // ends the collection window — without it the polls stay invisible.
  const polled = Promise.all([
    page.waitForResponse((r) => /\/kaapana-backend\/monitoring\/query\//.test(r.url())),
    page.waitForResponse((r) => r.url().includes('/kube-helm-api/pending-applications-count')),
  ])
  await page.clock.runFor(15_000)
  await polled

  expect(unscoped).toEqual([])
})

test('without a project prefix the view redirects onto the first project', async ({ page }) => {
  await installMockBackend(page)
  await seedShellState(page)
  await page.goto(UNSCOPED_VIEW_PATH)
  await page.waitForURL(`**${VIEW_PATH}`)
  await expect(page.getByText('You are working in project')).toContainText(defaultProject.name)
})
