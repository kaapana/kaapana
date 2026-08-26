import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  selectDag,
  shellProjects,
  viewPathFor,
  workflowField,
} from './fixtures/mock-backend'

// The four services base-ui's httpClient rewrites onto /project/<short_id>/
// (its PROJECT_SCOPED allowlist). Matched anywhere in the path so a call that
// bypasses the interceptor entirely is still caught.
const PROJECT_SCOPED_SERVICE = /(^|\/)(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

// The /project/<short_id> document prefix IS the project selection. This view
// has no project store — served without the prefix it just sends its calls
// unscoped — so there is no redirect-onto-first-project case to cover here.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const project = shellProjects[1]
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kaapana-backend/`),
  )
  await page.goto(viewPathFor(project))
  await scoped
})

// The presence assertion above stays green if a NEW call goes out unscoped
// (skipping httpClient or its allowlist), so assert the absence too. /aii,
// oauth2 and static assets are unprefixed by design.
// The collector only sees what happens before the last await, so the window
// must cover the whole flow, boot through submit — not just first paint.
test('no request to a project-scoped service escapes the /project/<slug>/ prefix', async ({
  page,
}) => {
  const project = shellProjects[1]
  const prefix = `/project/${project.short_id}/`
  const unscoped: string[] = []
  page.on('request', (r) => {
    const { pathname } = new URL(r.url())
    if (PROJECT_SCOPED_SERVICE.test(pathname) && !pathname.startsWith(prefix)) {
      unscoped.push(`${r.method()} ${pathname}`)
    }
  })

  await seedShellState(page)
  await installMockBackend(page)
  // This view schedules no poll; the runFor below asserts that rather than
  // assumes it — a timer-deferred request would land inside the window.
  await page.clock.install()
  // Barrier tied to the boot RESPONSE, matched without a prefix so it holds
  // whether or not the call is scoped; the DOM barrier below alone can be
  // satisfied before the last of the chained calls goes out.
  const schemas = page.waitForResponse((r) =>
    r.url().includes('/kaapana-backend/client/get-ui-form-schemas'),
  )
  await page.goto(viewPathFor(project))
  await schemas
  // The DAG field renders only after every request the view issues on load.
  await workflowField(page).waitFor({ state: 'visible' })

  // Interaction phase: the rest of the execution flow, and the view's only write.
  await selectDag(page, 'mock-all-fields')
  await page.getByLabel('Text Field').fill('edited')

  // Nothing is expected to fire here — that IS the assertion. Advanced before
  // the submit hand-off replaces the document (which would cancel pending
  // timers); with the clock faked this ends the collection window.
  await page.clock.runFor(15_000)
  await expect(page.getByLabel('Text Field')).toHaveValue('edited')

  const submitted = page.waitForResponse(
    (r) =>
      r.url().includes('/kaapana-backend/client/workflow') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Start Workflow' }).click()
  await submitted
  // The wrapper hands off to the (stubbed) shell workflow list on success, so
  // the window closes only once that navigation has happened.
  await page.waitForURL('**/workflows/workflows')

  expect(unscoped).toEqual([])
})
