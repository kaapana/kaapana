import { test, expect, type Page } from '@playwright/test'
import { installMockBackend, stubView } from './fixtures/mock-backend'

// Exercises the view->shell messages beyond kaapana:view-dirty (covered in
// view-dirty.spec.ts): kaapana:navigate and kaapana:project-switch, handled in
// App.vue.

// Posting on the shell document is equivalent to an iframe posting to its
// parent: the handler only checks event.origin, which is the same either way.
async function postFromView(page: Page, data: Record<string, unknown>) {
  await page.evaluate((d) => window.postMessage(d, window.location.origin), data)
}

// A value on the shell's window survives router.push but not a document load,
// so it distinguishes "the shell navigated" from "the shell was reloaded".
async function markShell(page: Page) {
  await page.evaluate(() => ((window as unknown as { __alive: boolean }).__alive = true))
}
const shellAlive = (page: Page) =>
  page.evaluate(() => (window as unknown as { __alive?: boolean }).__alive === true)

// Reports itself dirty on click, so the guard has something to protect.
async function stubDirtyView(page: Page, pathPrefix: string) {
  await page.route(`**${pathPrefix}**`, (r) =>
    r.fulfill({
      status: 200,
      contentType: 'text/html',
      body:
        `<!doctype html><html><body data-stub="dirty">` +
        `<button id="make-dirty" onclick="parent.postMessage(` +
        `{type:'kaapana:view-dirty',dirty:true}, location.origin)">dirty</button>` +
        `</body></html>`,
    }),
  )
}

async function makeDirty(page: Page) {
  await page.evaluate(() =>
    window.addEventListener('message', (e) => {
      if (e.data?.type === 'kaapana:view-dirty') document.body.dataset.dirtySeen = 'true'
    }),
  )
  await page.frameLocator('iframe.kaapana-iframe').locator('#make-dirty').click()
  await page.locator('body[data-dirty-seen]').waitFor()
}

test('kaapana:navigate opens the requested view without reloading the shell', async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await stubView(page, '/workflow-list-ui')
  await page.goto('/')
  await expect(page).toHaveURL(/\/project\//) // shell booted; earlier posts are lost
  await markShell(page)

  await postFromView(page, { type: 'kaapana:navigate', path: '/web/workflows/workflows' })

  await expect(page).toHaveURL(/\/project\/admin\/workflows\/workflows$/)
  expect(await shellAlive(page)).toBe(true)
})

// Naive resolution of the "-" placeholder section yields no entry, reporting
// a perfectly installed view as unavailable.
test('kaapana:navigate resolves a top-level entry addressed with "-"', async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await stubView(page, '/extensions-ui')
  await page.goto('/')
  await expect(page).toHaveURL(/\/project\//)

  await postFromView(page, { type: 'kaapana:navigate', path: '/web/-/extensions' })

  await expect(page).toHaveURL(/\/project\/admin\/extensions$/)
  await expect(page.getByText('View unavailable')).toHaveCount(0)
})

test('kaapana:navigate to an unknown view reports it instead of bouncing home', async ({
  page,
}) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await page.goto('/')
  await expect(page).toHaveURL(/\/project\//)
  const before = page.url()

  await postFromView(page, { type: 'kaapana:navigate', path: '/web/workflows/not-installed' })

  await expect(page.getByText('View unavailable')).toBeVisible()
  await expect(page.getByText('/web/workflows/not-installed')).toBeVisible()
  expect(page.url()).toBe(before)

  await page.getByRole('button', { name: 'Close' }).click()
  await expect(page.getByText('View unavailable')).toHaveCount(0)
})

test('kaapana:navigate honours the unsaved-changes guard', async ({ page }) => {
  await installMockBackend(page)
  await stubDirtyView(page, '/data-gallery-ui')
  await stubView(page, '/workflow-list-ui')
  await page.goto('/')
  await expect(page).toHaveURL(/\/project\//)
  const before = page.url()

  await makeDirty(page)
  await postFromView(page, { type: 'kaapana:navigate', path: '/web/workflows/workflows' })

  await expect(page.getByText('Unsaved changes', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Stay' }).click()
  expect(page.url()).toBe(before)
})

test('kaapana:project-switch swaps the prefix and keeps the route', async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await page.goto('/')
  await expect(page).toHaveURL(/\/project\//)
  await markShell(page)
  const routeBefore = new URL(page.url()).pathname.replace(/^\/project\/[^/]+/, '')

  await postFromView(page, { type: 'kaapana:project-switch', slug: 'resb' })

  await expect(page).toHaveURL(new RegExp(`/project/resb${routeBefore}$`))
  await expect(page.locator('.project-select')).toContainText(/research-b/i)
  // switched in place — the shell itself was never reloaded
  expect(await shellAlive(page)).toBe(true)
})

test('kaapana:project-switch ignores a project the user does not have', async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  await page.goto('/')
  await expect(page).toHaveURL(/\/project\//)
  const before = page.url()

  await postFromView(page, { type: 'kaapana:project-switch', slug: 'not-mine' })

  await expect(page).toHaveURL(before)
  await expect(page.getByText('View unavailable')).toHaveCount(0)
})
