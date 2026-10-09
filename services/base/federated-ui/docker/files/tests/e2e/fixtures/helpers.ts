import { expect, type Locator, type Page } from '@playwright/test'
import { defaultMockData, installMockBackend, seedShellState, VIEW_PATH, type MockData } from './mock-backend'

export async function openView(page: Page, data: MockData = defaultMockData, path = VIEW_PATH) {
  await seedShellState(page)
  await installMockBackend(page, data)
  await page.goto(path)
  await expect(page.getByTestId('summary')).not.toHaveText('Loading instances…')
}

export function card(page: Page, name: string): Locator {
  return page.getByTestId(`instance-${name}`)
}

export function field(scope: Locator, label: string): Locator {
  return scope.locator(`.instance-field[data-field="${label}"]`)
}

export function dialog(page: Page): Locator {
  return page.getByRole('dialog').last()
}

export function toasts(page: Page): Locator {
  return page.locator('.vue-notification-wrapper')
}

export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

export function failRoute(page: Page, url: RegExp, detail: string, status = 500) {
  return page.route(url, (r) => r.fulfill(serverError(detail, status)))
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

export function countRequests(page: Page, url: RegExp, method?: string): () => number {
  let count = 0
  page.on('request', (r) => {
    if (url.test(r.url()) && (!method || r.method() === method)) count++
  })
  return () => count
}

export function nextRequest(page: Page, url: RegExp, method: string) {
  return page.waitForRequest((r) => url.test(r.url()) && r.method() === method)
}

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

export async function dismissWithEscape(page: Page) {
  await expect(dialog(page)).toBeVisible()
  await pressEscapeUntil(page, async () => (await page.getByRole('dialog').count()) === 0)
}
