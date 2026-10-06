import { expect, type Page } from '@playwright/test'
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
