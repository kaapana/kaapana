import { test, expect } from '@playwright/test'
import { installMockBackend, PROJECT_SLUGS, viewPathFor } from './fixtures/mock-backend'

// The four services base-ui's httpClient rewrites onto /project/<short_id>/
// (its PROJECT_SCOPED allowlist). Matched anywhere in the path so a call that
// bypasses the interceptor entirely is still caught.
const PROJECT_SCOPED_SERVICE = /(^|\/)(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

// The /project/<short_id> document prefix IS the project selection. This view
// has no project store — served without the prefix it just sends its calls
// unscoped — so there is no redirect-onto-first-project case to cover here.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await installMockBackend(page)
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const slug = PROJECT_SLUGS[1]
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${slug}/kaapana-backend/`),
  )
  await page.goto(viewPathFor(slug))
  await scoped
})

// The presence assertion above stays green if a NEW call goes out unscoped
// (skipping httpClient or its allowlist), so assert the absence too. /aii,
// oauth2 and static assets are unprefixed by design.
// The collector only sees what happens before the last await, so the window
// must cover interaction and one poll tick, not just the boot fetch.
test('no request to a project-scoped service escapes the /project/<slug>/ prefix', async ({
  page,
}) => {
  const slug = PROJECT_SLUGS[1]
  const unscoped: string[] = []
  page.on('request', (r) => {
    const { pathname } = new URL(r.url())
    if (PROJECT_SCOPED_SERVICE.test(pathname) && !pathname.startsWith(`/project/${slug}/`)) {
      unscoped.push(`${r.method()} ${pathname}`)
    }
  })

  await installMockBackend(page)
  // Fake clock so the 15s poll lands inside the window (see the closing runFor).
  await page.clock.install()
  // Barrier tied to the boot RESPONSE, matched without a prefix so it holds
  // whether or not the call is scoped; a DOM-only barrier can be satisfied
  // before the request goes out.
  const listed = page.waitForResponse((r) =>
    /\/kaapana-backend\/client\/workflows(\?|$)/.test(r.url()),
  )
  await page.goto(viewPathFor(slug))
  await listed
  await expect(page.getByText('running-wf', { exact: true })).toBeVisible()

  // Expanding a row is the view's second read path (GET /jobs per workflow).
  const jobs = page.waitForResponse((r) => /\/kaapana-backend\/client\/jobs(\?|$)/.test(r.url()))
  await page.getByText('running-wf', { exact: true }).click()
  await jobs
  await expect(page.getByText('dag-alpha')).toBeVisible()

  // A job write (PUT /job) — the only non-GET the view issues.
  const aborted = page.waitForResponse(
    (r) => /\/kaapana-backend\/client\/job(\?|$)/.test(r.url()) && r.request().method() === 'PUT',
  )
  await page
    .locator('td .v-data-table')
    .getByRole('row')
    .filter({ hasText: 'dag-alpha' })
    .locator('button:has(.mdi-stop-circle-outline)')
    .click()
  await aborted

  // Searching re-queries the list with the term.
  const searched = page.waitForResponse((r) => r.url().includes('search=running'))
  await page.getByLabel('Search for Workflow').fill('running')
  await searched

  // One tick of the 15s list poll; with the clock faked, this advance is what
  // ends the collection window — without it the poll is invisible to the spec.
  const polled = page.waitForResponse((r) =>
    /\/kaapana-backend\/client\/workflows(\?|$)/.test(r.url()),
  )
  await page.clock.runFor(15_000)
  await polled

  expect(unscoped).toEqual([])
})
