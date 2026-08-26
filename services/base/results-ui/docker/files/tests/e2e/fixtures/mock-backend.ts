import type { Page } from '@playwright/test'

// Path the view is served under standalone (vite `base` / router history base).
export const UNSCOPED_VIEW_PATH = '/results-ui/'
// Path the shell serves the view under: the /project/<short_id> document
// prefix IS the project selection (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/results-ui/'

// Mirrors the REAL backend node shape (get-static-website-results-tree): EVERY
// node carries `children: []` plus a `hasChildren` discriminator — files
// included. That honesty is what reproduces the Vuetify bogus-expand-toggle bug.
export interface MockTreeNode {
  name: string
  path: string
  url?: string
  file?: string | false
  children?: MockTreeNode[]
  hasChildren?: boolean
  nextContinuationToken?: string | null
}

export interface ResultsPayload {
  items: MockTreeNode[]
  nextContinuationToken: string | null
}

// `root` is the first page of the top-level listing; `children` is keyed by
// folder path (the `prefix` param); `pages` by continuation token (root and
// per-folder paging alike).
export interface MockData {
  userinfo: { preferredUsername: string; groups: string[]; user: string }
  root: ResultsPayload
  children: Record<string, ResultsPayload>
  pages: Record<string, ResultsPayload>
}

const url = (p: string) => `/minio-console/download/results/${p}`

const folder = (name: string, path: string): MockTreeNode => ({
  name,
  path,
  file: false,
  children: [],
  hasChildren: true,
})
const file = (name: string, path: string, kind: string): MockTreeNode => ({
  name,
  path,
  file: kind,
  children: [],
  hasChildren: false,
  url: url(path),
})

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  root: {
    items: [
      folder('nnunet-training-230101', 'nnunet-training-230101/'),
      folder('total-segmentator-230102', 'total-segmentator-230102/'),
      folder('batch-run-230104', 'batch-run-230104/'),
      file('overview.html', 'overview.html', 'html'),
    ],
    nextContinuationToken: null,
  },
  children: {
    'nnunet-training-230101/': {
      items: [
        file('report.html', 'nnunet-training-230101/report.html', 'html'),
        file('metrics.json', 'nnunet-training-230101/metrics.json', 'json'),
      ],
      nextContinuationToken: null,
    },
    'total-segmentator-230102/': {
      items: [file('segmentation.pdf', 'total-segmentator-230102/segmentation.pdf', 'pdf')],
      nextContinuationToken: null,
    },
    // Crosses the >10 confirm threshold only once an UNLOADED subfolder is
    // descended into AND its continuation page is fetched (4 + 5 + 2 = 11 files),
    // so the cascade's fetch-descendants + follow-tokens path is exercised.
    'batch-run-230104/': {
      items: [
        file('b1.html', 'batch-run-230104/b1.html', 'html'),
        file('b2.html', 'batch-run-230104/b2.html', 'html'),
        file('b3.html', 'batch-run-230104/b3.html', 'html'),
        file('b4.html', 'batch-run-230104/b4.html', 'html'),
        folder('part-b', 'batch-run-230104/part-b/'),
      ],
      nextContinuationToken: null,
    },
    'batch-run-230104/part-b/': {
      items: [
        file('p1.html', 'batch-run-230104/part-b/p1.html', 'html'),
        file('p2.html', 'batch-run-230104/part-b/p2.html', 'html'),
        file('p3.html', 'batch-run-230104/part-b/p3.html', 'html'),
        file('p4.html', 'batch-run-230104/part-b/p4.html', 'html'),
        file('p5.html', 'batch-run-230104/part-b/p5.html', 'html'),
      ],
      nextContinuationToken: 'batch-run-230104/part-b/p5.html',
    },
  },
  pages: {
    'batch-run-230104/part-b/p5.html': {
      items: [
        file('p6.html', 'batch-run-230104/part-b/p6.html', 'html'),
        file('p7.html', 'batch-run-230104/part-b/p7.html', 'html'),
      ],
      nextContinuationToken: null,
    },
  },
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

function emptyPayload(): ResultsPayload {
  return { items: [], nextContinuationToken: null }
}

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: { short_id: string }): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

/**
 * Seed the same-origin state the portal-ui shell writes before an embedded view
 * boots: localStorage["settings"]. The project is NOT seeded — it travels in
 * the document URL (/project/<short_id>/...).
 */
export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
  })
}

/**
 * Intercept every backend call this view makes so it boots without a platform.
 * Call before page.goto(). Later page.route overrides win — add error-response
 * routes after this call.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  // Auth: prod build asks the oauth2 proxy, dev server a static token file.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))

  // The single data endpoint. Route on prefix/continuation_token query params.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    const u = new URL(r.request().url())
    const prefix = u.searchParams.get('prefix')
    const token = u.searchParams.get('continuation_token')
    let payload: ResultsPayload
    if (token) {
      payload = data.pages[token] ?? emptyPayload()
    } else if (prefix) {
      payload = data.children[prefix] ?? emptyPayload()
    } else {
      payload = data.root
    }
    r.fulfill(json(payload))
  })

  // File preview/open targets: the iframe src and window.open both point at the
  // node `url`. Stub them so neither the embedded iframe nor a popup hangs.
  await page.route('**/minio-console/**', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html><body data-stub="result-file">result file</body></html>',
    }),
  )
}
