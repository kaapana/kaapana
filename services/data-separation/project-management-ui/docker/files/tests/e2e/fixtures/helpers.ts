import { expect, type Locator, type Page } from '@playwright/test'
import type { ProjectItem } from '@/common/types'
import {
  defaultMockData,
  installMockBackend,
  projectPath,
  VIEW_PATH,
  type MockData,
} from './mock-backend'

/** A FastAPI-style failure body, as AII and kube-helm raise them. */
export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

/** Make every `method` request whose URL matches `path` fail until it is unrouted. */
export function failRoute(page: Page, method: string, path: RegExp, detail: string, status = 500) {
  return page.route(path, (r) =>
    r.request().method() === method ? r.fulfill(serverError(detail, status)) : r.fallback(),
  )
}

/** Let the requests to `path` succeed again and retry from the failure message. */
export async function retryFrom(page: Page, alert: Locator, path: RegExp) {
  await page.unroute(path)
  await alert.getByRole('button', { name: 'Try again' }).click()
  await expect(alert).toBeHidden()
}

export function nextRequest(page: Page, method: string, url: string) {
  return page.waitForRequest((r) => r.url().includes(url) && r.method() === method)
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

type OpenOptions = { seedSettings?: boolean; routes?: (page: Page) => Promise<unknown> }

/**
 * Boot the project list against the mock backend and wait until the first
 * load has landed. `routes` runs after the mock backend is installed and
 * before navigation, for overrides that must win over the defaults.
 * Returns the mock backend's state.
 */
export async function openView(
  page: Page,
  data: MockData = defaultMockData,
  options: OpenOptions = {},
) {
  const state = await installMockBackend(page, data, { seedSettings: options.seedSettings })
  await options.routes?.(page)
  await page.goto(VIEW_PATH)
  await expect(row(page, data.projects[0].name)).toBeVisible()
  return state
}

/** Boot a project's detail page and wait until its header is loaded. */
export async function openProject(
  page: Page,
  project: ProjectItem,
  data: MockData = defaultMockData,
  options: OpenOptions = {},
) {
  const state = await installMockBackend(page, data, { seedSettings: options.seedSettings })
  await options.routes?.(page)
  await page.goto(projectPath(project))
  await expect(page.getByText(project.name, { exact: true }).first()).toBeVisible()
  return state
}

export function row(page: Page, name: string) {
  return page.getByRole('row').filter({ hasText: name })
}

export function dialog(page: Page) {
  return page.getByRole('dialog')
}

export async function confirmAction(page: Page, name: string) {
  const button = dialog(page).getByRole('button', { name, exact: true })
  await expect(button, `no confirm button labelled "${name}"`).toBeVisible({ timeout: 5_000 })
  await button.click()
  await dialog(page).waitFor({ state: 'hidden' })
}

/**
 * Press Escape until `settled` holds. Vuetify honours Escape only once its
 * overlay stack has settled, which happens in a setTimeout after the dialog
 * appears; under load a first Escape can be swallowed. A repeat comes only
 * after a second without the expected outcome, long enough for a press that
 * did take effect to show it.
 */
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
  await pressEscapeUntil(page, () => dialog(page).isHidden())
}

// Content can still shift when the height animation ends; a click that
// straddles the shift lands on no element.
export async function waitForExpandTransition(page: Page) {
  await expect(page.locator('.expand-transition-enter-active')).toHaveCount(0)
}

export async function expandSection(page: Page, title: string) {
  await page.getByRole('heading', { name: title }).click()
  await waitForExpandTransition(page)
}

export function toasts(page: Page) {
  return page.locator('.vue-notification-wrapper')
}

export async function openFailureDetails(page: Page, title: string) {
  const toast = toasts(page).filter({ hasText: title })
  await expect(toast).toBeVisible()
  await toast.click()
  await expect(dialog(page).getByText(title, { exact: true })).toBeVisible()
  return dialog(page)
}
