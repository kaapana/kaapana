import { expect, type Page } from '@playwright/test'
import {
  defaultMockData,
  installMockBackend,
  logsPath,
  RUNS_PATH,
  WORKFLOWS_PATH,
  type MockData,
  type MockRecorder,
} from './mock-backend'

// Shared vocabulary for the specs: how to boot each page, how to find its
// parts, and how to make the backend fail. The specs own the assertions.

/** A FastAPI-style failure body, as workflow-api raises them. */
export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

/** Make every call matching `url` fail from now on. */
export function failRoute(page: Page, url: string | RegExp, detail: string, status = 500) {
  return page.route(url, (r) => r.fulfill(serverError(detail, status)))
}

/** Counts requests matching `url` from now on; call the returned function to read. */
export function countRequests(page: Page, url: RegExp): () => number {
  let count = 0
  page.on('request', (r) => {
    if (url.test(r.url())) count++
  })
  return () => count
}

type Setup = { data?: MockData; routes?: (page: Page) => Promise<unknown> }

async function open(page: Page, path: string, { data = defaultMockData(), routes }: Setup) {
  const recorder = await installMockBackend(page, data)
  await routes?.(page)
  await page.goto(path)
  return recorder
}

export async function openWorkflows(page: Page, setup: Setup = {}): Promise<MockRecorder> {
  const recorder = await open(page, WORKFLOWS_PATH, setup)
  await expect(page.getByRole('heading', { name: 'Workflows', level: 1 })).toBeVisible()
  return recorder
}

export async function openRuns(page: Page, setup: Setup = {}): Promise<MockRecorder> {
  const recorder = await open(page, RUNS_PATH, setup)
  await expect(page.getByRole('heading', { name: 'Workflow runs', level: 1 })).toBeVisible()
  return recorder
}

export async function openLogs(
  page: Page,
  runId: number,
  setup: Setup = {},
): Promise<MockRecorder> {
  return open(page, logsPath(runId), setup)
}

export function card(page: Page, title: string) {
  return page.getByTestId('workflow-card').filter({ has: page.getByText(title, { exact: true }) })
}

export function runRow(page: Page, runId: number) {
  return page.locator(`[data-testid="run-row"][data-run-id="${runId}"]`)
}

export function runRows(page: Page) {
  return page.getByTestId('run-row')
}

/** The dialog that is currently open. */
export function dialog(page: Page) {
  return page.getByRole('dialog')
}

/** The transient notifications currently on screen. */
export function toasts(page: Page) {
  return page.locator('.vue-notification-wrapper')
}

/**
 * Press Escape until `settled` holds. Vuetify honours Escape only once its
 * overlay stack has settled, which happens in a setTimeout after the dialog
 * appears; under load a first Escape can be swallowed.
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

/** Open the details dialog behind a failure notification. */
export async function openFailureDetails(page: Page, title: string) {
  const toast = toasts(page).filter({ hasText: title })
  await expect(toast).toBeVisible()
  await toast.click()
  const details = dialog(page).filter({ hasText: 'Copy details' })
  await expect(details).toBeVisible()
  return details
}

/** Record every postMessage the view sends to its shell. */
export async function recordShellMessages(page: Page) {
  await page.addInitScript(() => {
    ;(window as any).__shellMessages = []
    window.addEventListener('message', (event: MessageEvent) => {
      ;(window as any).__shellMessages.push(event.data)
    })
  })
  return () => page.evaluate(() => (window as any).__shellMessages as unknown[])
}

/** Start a workflow from its card and wait for the form. */
export async function openRunForm(page: Page, title: string) {
  const start = card(page, title).getByRole('button', { name: 'Start' })
  await expect(start).toBeEnabled()
  await start.click()
  const form = dialog(page)
  await expect(form.getByText(`Start ${title}`)).toBeVisible()
  return form
}
