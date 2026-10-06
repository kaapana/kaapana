import { expect, type Page } from '@playwright/test'
import {
  PROJECT_VIEW_PATH,
  VIEW_PATH,
  defaultMockData,
  installMockBackend,
  type MockBackend,
  type MockData,
} from './mock-backend'

export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

export function failRoute(page: Page, path: RegExp, detail: string, status = 500, method?: string) {
  return page.route(
    (url) => path.test(url.pathname),
    (route) => {
      if (method && route.request().method() !== method) return route.fallback()
      return route.fulfill(serverError(detail, status))
    },
  )
}

export async function openView(
  page: Page,
  data: MockData = defaultMockData(),
  options: {
    scoped?: boolean
    query?: string
    seedSettings?: boolean
    routes?: (page: Page) => Promise<unknown>
    waitFor?: 'cards' | 'none'
  } = {},
): Promise<MockBackend> {
  const backend = await installMockBackend(page, data, { seedSettings: options.seedSettings })
  await options.routes?.(page)
  const base = options.scoped === false ? VIEW_PATH : PROJECT_VIEW_PATH
  await page.goto(`${base}${options.query ?? ''}`)
  if (options.waitFor !== 'none' && data.entities.length) {
    await expect(cards(page).first()).toBeVisible()
  }
  return backend
}

export function cards(page: Page) {
  return page.getByTestId('entity-card')
}

export function card(page: Page, id: string) {
  return cards(page).filter({ hasText: id })
}

export function dialog(page: Page) {
  return page.getByRole('dialog').last()
}

export function toasts(page: Page) {
  return page.locator('.vue-notification-wrapper')
}

export async function openEntity(page: Page, id: string) {
  await card(page, id)
    .getByRole('button', { name: `Show details of entity ${id}` })
    .click()
  const detail = page.getByTestId('entity-detail')
  await expect(detail).toBeVisible()
  return detail
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

export function lastRequest(backend: MockBackend, method: string, pathEnd: string | RegExp) {
  const matches = backend.requests.filter(
    (request) =>
      request.method === method &&
      (typeof pathEnd === 'string' ? request.path.endsWith(pathEnd) : pathEnd.test(request.path)),
  )
  return matches[matches.length - 1]
}
