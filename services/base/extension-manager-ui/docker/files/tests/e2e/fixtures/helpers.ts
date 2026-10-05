import { expect, type Page } from '@playwright/test'
import { defaultMockData, installMockBackend, VIEW_PATH, type MockData } from './mock-backend'

export const API = {
  repositories: '/extensions-api/repositories',
  extensions: '/extensions-api/extensions',
  install: '/extensions-api/extensions/install',
} as const

export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

export function failRoute(
  page: Page,
  url: string | RegExp,
  detail: string,
  status = 500,
  method?: string,
) {
  const pattern =
    typeof url === 'string'
      ? new RegExp(`${url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\?.*)?$`)
      : url
  return page.route(pattern, (route) => {
    if (method && route.request().method() !== method) return route.fallback()
    return route.fulfill(serverError(detail, status))
  })
}

export function nextRequest(page: Page, url: string, method: string) {
  return page.waitForRequest(
    (request) => request.url().includes(url) && request.method() === method,
  )
}

export function countRequests(page: Page, url: string, method = 'GET'): () => number {
  let count = 0
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.endsWith(url) && request.method() === method) count++
  })
  return () => count
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(String(error)))
  return errors
}

export async function openView(
  page: Page,
  section: 'catalog' | 'extensions' | 'repositories' = 'catalog',
  data: MockData = defaultMockData(),
  options: {
    seedSettings?: boolean
    routes?: (page: Page) => Promise<unknown>
    waitFor?: 'cards' | 'empty'
  } = {},
): Promise<MockData> {
  const state = await installMockBackend(page, data, { seedSettings: options.seedSettings })
  await options.routes?.(page)
  await page.goto(`${VIEW_PATH}${section}`)
  if (options.waitFor === 'empty') {
    await expect(page.getByTestId('empty-state')).toBeVisible()
  } else if (options.waitFor !== undefined || hasItems(section, state)) {
    await expect(cards(page).first()).toBeVisible()
  }
  return state
}

function hasItems(section: string, data: MockData): boolean {
  if (section === 'extensions') return data.extensions.length > 0
  if (section === 'repositories') return data.repositories.length > 0
  return Object.values(data.manifests).some((list) => list.length > 0)
}

export function cards(page: Page) {
  return page.getByTestId('card')
}

export function card(page: Page, name: string) {
  return cards(page).filter({
    has: page.locator('.v-card-title', { hasText: new RegExp(`^${name}$`) }),
  })
}

export function dialog(page: Page) {
  return page.getByRole('dialog').last()
}

export function toasts(page: Page) {
  return page.locator('.vue-notification-wrapper')
}

export async function confirmAction(page: Page, name: string) {
  const button = dialog(page).getByRole('button', { name, exact: true })
  await expect(button, `no confirm button labelled "${name}"`).toBeVisible({ timeout: 5_000 })
  await button.click()
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

export async function openFailureDetails(page: Page, title: string) {
  const toast = toasts(page).filter({ hasText: title })
  await expect(toast).toBeVisible()
  await toast.click()
  const details = page.getByRole('dialog').filter({ hasText: 'Copy details' })
  await expect(details.getByText(title, { exact: true })).toBeVisible()
  return details
}

export async function recordShellMessages(page: Page) {
  await page.addInitScript(() => {
    ;(window as unknown as { __shellMessages: unknown[] }).__shellMessages = []
    window.addEventListener('message', (event: MessageEvent) => {
      ;(window as unknown as { __shellMessages: unknown[] }).__shellMessages.push(event.data)
    })
  })
  return () =>
    page.evaluate(
      () =>
        (window as unknown as { __shellMessages: { type: string; dirty?: boolean }[] })
          .__shellMessages,
    )
}
