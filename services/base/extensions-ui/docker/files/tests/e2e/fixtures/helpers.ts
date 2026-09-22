import { expect, type Page } from '@playwright/test'
import {
  defaultMockData,
  installMockBackend,
  VIEW_PATH,
  type AvailableVersionMock,
  type ExtensionMock,
  type MockData,
} from './mock-backend'

// Shared vocabulary for the specs: how to boot the view, how to build a
// catalogue row, and how to observe the kube-helm calls. Everything here is
// behaviour-neutral; the specs own the assertions.

/* ------------------------------------------------------------- backend --- */

export const HELM = {
  extensions: /\/kube-helm-api\/extensions(\?.*)?$/,
  install: '/kube-helm-api/helm-install-chart',
  uninstall: '/kube-helm-api/helm-delete-chart',
  update: '/kube-helm-api/update-extensions',
  importContainer: '/kube-helm-api/import-container',
  upload: '/kube-helm-api/filepond-upload',
} as const

/** A FastAPI-style failure body, as kube-helm and aii raise them. */
export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

/** Make every call matching `url` fail from now on. */
export function failRoute(page: Page, url: string | RegExp, detail: string, status = 500) {
  const pattern = typeof url === 'string' ? `**${url}*` : url
  return page.route(pattern, (r) => r.fulfill(serverError(detail, status)))
}

/** Resolves with the JSON body of the next POST to `url`. */
export function nextPost(page: Page, url: string): Promise<any> {
  return page
    .waitForRequest((r) => r.url().includes(url) && r.method() === 'POST')
    .then((r) => r.postDataJSON())
}

/** Counts requests to `url` from now on; call the returned function to read. */
export function countRequests(page: Page, url: string): () => number {
  let count = 0
  page.on('request', (r) => {
    if (r.url().includes(url)) count++
  })
  return () => count
}

/** Collects uncaught page errors from now on. */
export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

/* --------------------------------------------------------------- data ---- */

const readyDeployment = (releaseName: string) => ({
  deployment_id: releaseName,
  helm_status: 'deployed',
  kube_status: 'Running',
  links: [],
  ready: true,
})

/** A version with one healthy deployment. */
export function deployed(releaseName: string): AvailableVersionMock {
  return { deployments: [readyDeployment(releaseName)] }
}

/**
 * A catalogue row with sensible defaults: single-install, stable, CPU,
 * not installed, one version. Override what the test is about.
 */
export function extension(
  overrides: Partial<ExtensionMock> & { releaseName: string },
): ExtensionMock {
  const version = overrides.version ?? '1.0.0'
  const name = overrides.name ?? overrides.releaseName
  return {
    name,
    chart_name: name,
    version,
    versions: [version],
    available_versions: { [version]: { deployments: [] } },
    multiinstallable: 'no',
    kind: 'application',
    experimental: 'no',
    resourceRequirement: 'cpu',
    successful: null,
    installed: 'no',
    description: '',
    display_name: overrides.releaseName,
    keywords: ['kaapana-application'],
    ...overrides,
  }
}

/** The default catalogue with its extension list replaced. */
export function catalogue(extensions: ExtensionMock[]): MockData {
  return { ...defaultMockData, extensions }
}

/* --------------------------------------------------------------- view ----- */

/**
 * Boot the view against the mock backend and wait until the first load has
 * landed: the first row when there is one, the table otherwise.
 * `routes` runs after the mock backend is installed and before navigation,
 * for overrides that must win over the defaults (later routes win).
 */
export async function openView(
  page: Page,
  data: MockData = defaultMockData,
  options: { seedSettings?: boolean; routes?: (page: Page) => Promise<unknown> } = {},
) {
  await installMockBackend(page, data, { seedSettings: options.seedSettings })
  await options.routes?.(page)
  await page.goto(VIEW_PATH)
  const first = data.extensions[0]
  if (first) {
    await expect(row(page, first.display_name)).toBeVisible()
  } else {
    await expect(page.getByRole('table')).toBeVisible()
  }
}

/** The table row for an extension, by display name. */
export function row(page: Page, displayName: string) {
  return page.getByRole('row', { name: displayName })
}

/** The dialog that is currently open. */
export function dialog(page: Page) {
  return page.getByRole('dialog')
}

/** The transient notifications currently on screen. */
export function toasts(page: Page) {
  return page.locator('.vue-notification-wrapper')
}
