import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, secondProject, viewPathFor } from './fixtures/mock-backend'

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
  // Deliberately NOT the default project, so a fallback-to-default would fail.
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${secondProject.short_id}/kaapana-backend/`),
  )
  await page.goto(viewPathFor(secondProject))
  await scoped
})

// The presence assertion above stays green if a NEW call goes out unscoped
// (skipping httpClient or its allowlist), so assert the absence too. oauth2
// and static assets are unprefixed by design.
// The collector only sees what happens before the last await, so the window
// must cover interaction and one poll tick, not just the boot fetch.
test('no request to a project-scoped service escapes the /project/<slug>/ prefix', async ({
  page,
}) => {
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
  // Fake clock so the 15s poll lands inside the window (see the closing runFor).
  await page.clock.install()
  // Barrier tied to the boot RESPONSE, matched without a prefix so it holds
  // whether or not the call is scoped; a DOM-only barrier can be satisfied
  // before the request goes out.
  const listed = page.waitForResponse((r) => /\/client\/get-kaapana-instances/.test(r.url()))
  await page.goto(viewPathFor(secondProject))
  await listed
  await expect(page.getByText('Instance name: central-node')).toBeVisible()

  // Sync remotes — a read the boot fetch never makes.
  const synced = page.waitForResponse((r) => /\/client\/check-for-remote-updates/.test(r.url()))
  await page.getByRole('button', { name: 'sync remotes' }).click()
  await synced

  // An inline edit + save on the local instance: the view's write path (PUT).
  const row = page
    .getByText('Automatically sync remotes:', { exact: true })
    .locator('xpath=ancestor::*[contains(concat(" ", @class, " "), " v-row ")][1]')
  await row.getByRole('button').click()
  await page.getByLabel('Check automatically for remote updates').click()
  const saved = page.waitForResponse(
    (r) => /\/client\/client-kaapana-instance/.test(r.url()) && r.request().method() === 'PUT',
  )
  await row.getByRole('button').click()
  await saved

  // One tick of the 15s instance poll; with the clock faked, this advance is
  // what ends the collection window — without it the poll is invisible.
  const polled = page.waitForResponse((r) => /\/client\/get-kaapana-instances/.test(r.url()))
  await page.clock.runFor(15_000)
  await polled

  expect(unscoped).toEqual([])
})
