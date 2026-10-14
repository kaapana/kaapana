import { test, expect, type Page } from '@playwright/test'
import { installMockBackend } from './fixtures/mock-backend'

// A stub view with a link to a deeper page of its own, so the iframe can move
// away from the entry's start page. Returns a hit counter per served path.
async function stubLinkedView(page: Page): Promise<() => string[]> {
  const served: string[] = []
  await page.route('**/data-gallery-ui**', (r) => {
    const path = new URL(r.request().url()).pathname
    served.push(path)
    return r.fulfill({
      status: 200,
      contentType: 'text/html',
      body:
        `<!doctype html><html><body data-path="${path}">` +
        `<a id="deeper" href="/project/admin/data-gallery-ui/deeper">deeper</a>` +
        `</body></html>`,
    })
  })
  return () => served
}

const DEEPER = '/project/admin/data-gallery-ui/deeper'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
})

test('Tab from the drawer reaches the corner controls, which appear while focused', async ({
  page,
}) => {
  await stubLinkedView(page)
  await page.goto('/')
  const overlay = page.locator('.iframe-overlay')
  await expect(overlay).toHaveCSS('opacity', '0')

  // The view can hold many controls, so the corner comes first after the drawer.
  await page.getByRole('button', { name: 'Log out' }).focus()
  await page.keyboard.press('Tab')

  await expect(page.getByRole('button', { name: 'Reload view' })).toBeFocused()
  await expect(overlay).toHaveCSS('opacity', '1')
  await expect(page.getByRole('button', { name: 'Open view in a new tab' })).toBeVisible()
})

test('open in a new tab uses the URL the iframe is on, not the entry start page', async ({
  page,
}) => {
  await stubLinkedView(page)
  await page.goto('/')
  const frame = page.frameLocator('iframe.kaapana-iframe')
  await frame.locator('#deeper').click()
  await expect(frame.locator('body')).toHaveAttribute('data-path', DEEPER)

  const popupPromise = page.waitForEvent('popup')
  // dispatchEvent sidesteps the hover-reveal, which the first test covers.
  await page.getByRole('button', { name: 'Open view in a new tab' }).dispatchEvent('click')
  const popup = await popupPromise

  await expect.poll(() => new URL(popup.url(), page.url()).pathname).toBe(DEEPER)
})

test('reload fetches the page the iframe is on again', async ({ page }) => {
  const served = await stubLinkedView(page)
  await page.goto('/')
  const frame = page.frameLocator('iframe.kaapana-iframe')
  await frame.locator('#deeper').click()
  await expect(frame.locator('body')).toHaveAttribute('data-path', DEEPER)
  expect(served().filter((p) => p === DEEPER)).toHaveLength(1)

  await page.getByRole('button', { name: 'Reload view' }).dispatchEvent('click')

  await expect.poll(() => served().filter((p) => p === DEEPER).length).toBe(2)
  await expect(frame.locator('body')).toHaveAttribute('data-path', DEEPER)
})

// Real views are single-page apps. They change the page with history.pushState
// instead of loading a new document, so the iframe fires no load event. This
// helper does the same.
async function pushDeeper(page: Page) {
  const frame = page.frameLocator('iframe.kaapana-iframe')
  await expect(frame.locator('#deeper')).toBeVisible()
  await frame.locator('body').evaluate((_, path) => history.pushState(null, '', path), DEEPER)
}

test('open in a new tab follows a single-page view to its current page', async ({ page }) => {
  await stubLinkedView(page)
  await page.goto('/')
  await pushDeeper(page)

  const popupPromise = page.waitForEvent('popup')
  await page.getByRole('button', { name: 'Open view in a new tab' }).dispatchEvent('click')
  const popup = await popupPromise

  await expect.poll(() => new URL(popup.url(), page.url()).pathname).toBe(DEEPER)
})

test('reload follows a single-page view to its current page', async ({ page }) => {
  const served = await stubLinkedView(page)
  await page.goto('/')
  await pushDeeper(page)
  expect(served()).not.toContain(DEEPER)

  await page.getByRole('button', { name: 'Reload view' }).dispatchEvent('click')

  await expect.poll(() => served().filter((p) => p === DEEPER).length).toBe(1)
})
