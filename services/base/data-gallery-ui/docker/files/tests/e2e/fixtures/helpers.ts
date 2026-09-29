import { expect, type Locator, type Page, type Request } from '@playwright/test'
import { bootGallery, makeDefaultMockData, VIEW_PATH, type MockData } from './mock-backend'

/* ------------------------------------------------------------- backend --- */

/** A URL fragment (matched anywhere in the URL) or a pattern. */
export type UrlMatcher = string | RegExp

function routePattern(url: UrlMatcher) {
  return typeof url === 'string' ? `**${url}*` : url
}

function urlMatches(requestUrl: string, url: UrlMatcher) {
  return typeof url === 'string' ? requestUrl.includes(url) : url.test(requestUrl)
}

export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

/** Fails matching calls from now on; later routes win over the mock backend's. */
export function failRoute(
  page: Page,
  url: UrlMatcher,
  detail: string,
  status = 500,
  method?: string,
) {
  return page.route(routePattern(url), (r) =>
    !method || r.request().method() === method
      ? r.fulfill(serverError(detail, status))
      : r.fallback(),
  )
}

export function delayRoute(page: Page, url: UrlMatcher, ms: number, method?: string) {
  return page.route(routePattern(url), async (r) => {
    if (!method || r.request().method() === method) {
      await new Promise((resolve) => setTimeout(resolve, ms))
    }
    // The page may have closed while the call was held.
    await r.fallback().catch(() => {})
  })
}

export function nextRequest(page: Page, url: UrlMatcher, method?: string): Promise<Request> {
  return page.waitForRequest((r) => urlMatches(r.url(), url) && (!method || r.method() === method))
}

export function nextPost(page: Page, url: UrlMatcher): Promise<any> {
  return nextRequest(page, url, 'POST').then((r) => r.postDataJSON())
}

export function countRequests(page: Page, url: UrlMatcher, method?: string): () => number {
  let count = 0
  page.on('request', (r) => {
    if (urlMatches(r.url(), url) && (!method || r.method() === method)) count++
  })
  return () => count
}

/** The POST that fetches the series list, as opposed to one series' metadata. */
export function isSeriesListRequest(req: Request): boolean {
  return req.method() === 'POST' && /\/dataset\/series$/.test(req.url())
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

/* --------------------------------------------------------------- view ----- */

/** Resolves once the first series card shows its metadata. */
export async function openGallery(
  page: Page,
  data: MockData = makeDefaultMockData(),
  url = VIEW_PATH,
) {
  await bootGallery(page, data, url)
  const first = data.seriesUids[0]
  const description = first ? data.seriesData[first]?.metadata['Series Description'] : undefined
  if (description) await expect(page.getByText(String(description))).toBeVisible()
}

export async function selectDataset(page: Page, label: string) {
  await page.getByLabel('Select Dataset').first().click()
  await page.getByRole('option', { name: label }).click()
}

export function dialog(page: Page, text?: string | RegExp): Locator {
  const dialogs = page.getByRole('dialog')
  return text === undefined ? dialogs : dialogs.filter({ hasText: text })
}

export function toasts(page: Page) {
  return page.locator('.vue-notification-wrapper')
}

/** Vuetify keeps tooltip content in the DOM, so a text query cannot tell open from closed. */
export function visibleTooltips(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll('.v-tooltip .v-overlay__content')]
      .filter((el) => (el as HTMLElement).offsetParent !== null)
      .map((el) => (el as HTMLElement).innerText.trim()),
  )
}

export async function confirmAction(page: Page, name: string) {
  const confirmation = dialog(page).filter({
    has: page.getByRole('button', { name, exact: true }),
  })
  const button = confirmation.getByRole('button', { name, exact: true })
  await expect(button, `no confirm button labelled "${name}"`).toBeVisible({ timeout: 5_000 })
  await button.click()
  await confirmation.waitFor({ state: 'hidden' })
}

/** Vuetify honours Escape only once its overlay stack has settled, in a setTimeout,
 *  so under load a first Escape can be swallowed; pressing again is safe. */
export async function pressEscapeUntil(page: Page, settled: () => Promise<boolean>) {
  for (let attempt = 0; attempt < 5; attempt++) {
    await page.keyboard.press('Escape')
    const deadline = Date.now() + 1_000
    while (Date.now() < deadline) {
      if (await settled()) return
      await page.waitForTimeout(50)
    }
  }
  throw new Error('Escape never took effect')
}

export async function dismissWithEscape(page: Page, target: Locator = dialog(page)) {
  await expect(target).toBeVisible()
  await pressEscapeUntil(page, () => target.isHidden())
}

/** Open the details dialog behind a failure notification. */
export async function openFailureDetails(page: Page, title: string) {
  const toast = toasts(page).filter({ hasText: title })
  await expect(toast).toBeVisible()
  await toast.click()
  await expect(dialog(page).getByText(title, { exact: true })).toBeVisible()
  return dialog(page)
}

/* ------------------------------------------------------------- shell ------ */

export async function trackDirty(page: Page) {
  await page.addInitScript(() => {
    ;(window as unknown as { __dirty: boolean[] }).__dirty = []
    window.addEventListener('message', (e: MessageEvent) => {
      if (e.data?.type === 'kaapana:view-dirty') {
        ;(window as unknown as { __dirty: boolean[] }).__dirty.push(e.data.dirty)
      }
    })
  })
}

export function lastDirty(page: Page) {
  return page.evaluate(() => {
    const d = (window as unknown as { __dirty: boolean[] }).__dirty
    return d.length ? d[d.length - 1] : null
  })
}
