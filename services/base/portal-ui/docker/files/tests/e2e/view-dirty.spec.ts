import { test, expect, type Page } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'
import type { Project } from '../../src/api/projects'

// Stub view with a button that posts kaapana:view-dirty on click — not on
// load, which would race IframeHost's clean-on-load reset. Returns a hit
// counter: a reload fetches the stub again, proving whether state was kept.
async function stubDirtyView(page: Page, pathPrefix: string): Promise<() => number> {
  let hits = 0
  await page.route(`**${pathPrefix}**`, (r) => {
    hits++
    return r.fulfill({
      status: 200,
      contentType: 'text/html',
      body:
        `<!doctype html><html><body data-stub="dirty">` +
        `<button id="make-dirty" onclick="parent.postMessage(` +
        `{type:'kaapana:view-dirty',dirty:true}, location.origin)">dirty</button>` +
        `</body></html>`,
    })
  })
  return () => hits
}

// The dirty postMessage is async: a fast follow-up action can beat the flag.
// The probe listener registers after the shell's, so once it fires the store
// update has already happened.
async function makeDirty(page: Page) {
  await page.evaluate(() =>
    window.addEventListener('message', (e) => {
      if (e.data?.type === 'kaapana:view-dirty') document.body.dataset.dirtySeen = 'true'
    }),
  )
  await page.frameLocator('iframe.kaapana-iframe').locator('#make-dirty').click()
  await page.locator('body[data-dirty-seen]').waitFor()
}

async function switchToResearchB(page: Page) {
  await page.locator('.project-select .v-field__input').click()
  await page.getByRole('option', { name: /research-b/ }).click()
}

const dialog = (page: Page) => page.getByText('Unsaved changes', { exact: true })

test('a clean view switches project without a confirm dialog', async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await page.goto('/')

  await switchToResearchB(page)

  await expect(page).toHaveURL(/\/project\/resb/)
  await expect(dialog(page)).toHaveCount(0)
})

test('a dirty view prompts on project switch and "Stay" keeps the current project', async ({
  page,
}) => {
  await installMockBackend(page)
  const galleryHits = await stubDirtyView(page, '/data-gallery-ui')
  await page.goto('/')

  await makeDirty(page)
  await switchToResearchB(page)

  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Stay' }).click()

  // hits staying 1 proves the iframe was not reloaded: the dirty state survived.
  await expect(page).toHaveURL(/\/project\/admin/)
  await expect(page.locator('.project-select')).toContainText(/admin/i)
  expect(galleryHits()).toBe(1)
})

test('a dirty view prompts on project switch and "Leave view" navigates, then the flag clears', async ({
  page,
}) => {
  await installMockBackend(page)
  await stubDirtyView(page, '/data-gallery-ui')
  await page.goto('/')

  await makeDirty(page)
  await switchToResearchB(page)

  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Leave view' }).click()
  await expect(page).toHaveURL(/\/project\/resb/)

  // The reloaded view starts clean (it only posts dirty on click), so switching
  // again goes straight through — proof the flag was cleared on the switch.
  await page.locator('.project-select .v-field__input').click()
  await page.getByRole('option', { name: /^admin/ }).click()
  await expect(page).toHaveURL(/\/project\/admin/)
  await expect(dialog(page)).toHaveCount(0)
})

test('menu navigation away from a dirty view prompts; "Stay" keeps URL and iframe state', async ({
  page,
}) => {
  await installMockBackend(page)
  const galleryHits = await stubDirtyView(page, '/data-gallery-ui')
  await stubView(page, '/extensions-ui')
  await page.goto('/')

  await makeDirty(page)
  await page.getByText('Extensions').click()

  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Stay' }).click()

  await expect(page).toHaveURL(/\/project\/admin$/)
  await expect(page.frameLocator('iframe.kaapana-iframe').locator('body')).toHaveAttribute(
    'data-stub',
    'dirty',
  )
  expect(galleryHits()).toBe(1)
})

test('menu navigation away from a dirty view prompts; "Leave view" navigates', async ({
  page,
}) => {
  await installMockBackend(page)
  await stubDirtyView(page, '/data-gallery-ui')
  await stubView(page, '/extensions-ui')
  await page.goto('/')

  await makeDirty(page)
  await page.getByText('Extensions').click()

  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Leave view' }).click()

  await expect(page).toHaveURL(/\/project\/admin\/extensions$/)
  await expect(page.frameLocator('iframe.kaapana-iframe').locator('body')).toHaveAttribute(
    'data-stub',
    'extensions-ui',
  )
})

test('the corner refresh on a dirty view prompts; "Stay" skips, "Leave view" reloads', async ({
  page,
}) => {
  await installMockBackend(page)
  const galleryHits = await stubDirtyView(page, '/data-gallery-ui')
  await page.goto('/')

  await makeDirty(page)
  // dispatchEvent sidesteps the hover-reveal of the corner overlay (opacity 0 /
  // pointer-events none until the hotspot is hovered), which is not under test.
  const refresh = page.locator('.iframe-overlay a').first()
  await refresh.dispatchEvent('click')

  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Stay' }).click()
  await expect(dialog(page)).toHaveCount(0)
  expect(galleryHits()).toBe(1)

  // Still dirty (no reload happened): a second refresh prompts again.
  await refresh.dispatchEvent('click')
  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Leave view' }).click()
  await expect.poll(galleryHits).toBe(2)
})

test('the footer "Log out" on a dirty view prompts; "Stay" keeps the session, "Leave view" logs out', async ({
  page,
}) => {
  await installMockBackend(page)
  await stubDirtyView(page, '/data-gallery-ui')
  // The logout target is a real top-window navigation; stub it so the assertion
  // is about the navigation and not about what the dev server serves for it.
  await page.route('**/kaapana-backend/oidc-logout', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>bye</body></html>' }),
  )
  await page.goto('/')

  await makeDirty(page)
  const logout = page.getByTitle('Log out')
  await logout.click()
  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Stay' }).click()
  await expect(dialog(page)).toHaveCount(0)
  await expect(page).toHaveURL(/\/project\//)

  // Still dirty: a second click prompts again, and "Leave view" logs out.
  await logout.click()
  await expect(dialog(page)).toBeVisible()
  await page.getByRole('button', { name: 'Leave view' }).click()
  await page.waitForURL('**/kaapana-backend/oidc-logout')
})

test('a forced retarget (selected project dropped) bypasses the confirm', async ({ page }) => {
  await page.clock.install()
  let projects: Project[] = defaultMockData.projects
  await installMockBackend(page)
  // Mutable /aii/projects (registered after installMockBackend so it wins).
  await page.route('**/aii/projects', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(projects) }),
  )
  await stubDirtyView(page, '/data-gallery-ui')
  await page.goto('/')

  await makeDirty(page)
  // The selected project (admin) is deleted; the next poll re-targets.
  projects = [{ id: 2, name: 'research-b', short_id: 'resb' }]
  await page.clock.runFor(15_000)

  await expect(page).toHaveURL(/\/project\/resb/)
  await expect(dialog(page)).toHaveCount(0)
})

test('a forced retarget dismisses an already-open confirm dialog', async ({ page }) => {
  await page.clock.install()
  let projects: Project[] = defaultMockData.projects
  await installMockBackend(page)
  await page.route('**/aii/projects', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(projects) }),
  )
  await stubDirtyView(page, '/data-gallery-ui')
  await stubView(page, '/extensions-ui')
  await page.goto('/')

  await makeDirty(page)
  await page.getByText('Extensions').click()
  await expect(dialog(page)).toBeVisible()

  // The retarget commits underneath the open dialog; the dialog must not
  // linger (its "Leave view" would act on a navigation that no longer exists).
  projects = [{ id: 2, name: 'research-b', short_id: 'resb' }]
  await page.clock.runFor(15_000)

  await expect(page).toHaveURL(/\/project\/resb/)
  await expect(dialog(page)).toBeHidden()
})
