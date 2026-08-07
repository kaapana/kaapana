import type { Page, Route } from '@playwright/test'
import type { DashboardData } from '@/api/dashboard'
import type { KaapanaNotification } from '@/api/notifications'

export interface UserinfoJwt {
  preferredUsername: string
  groups: string[]
  user: string
}

export interface PolicyData {
  endpoints_per_role: Record<string, { path: string; methods: string[] }[]>
}

// Everything the view fetches on boot + first render, in one overridable
// bundle. Handlers read from the bundle at request time, so tests may mutate
// it after installMockBackend (e.g. add a notification, then push a WS event).
export interface MockData {
  userinfo: UserinfoJwt
  policyData: PolicyData
  aiiUser: { id: string; realm_roles: string[] }
  projects: Array<{ id: number; name: string; short_id?: string; role_name?: string }>
  dashboard: DashboardData
  // Keyed by the short_id in the request's /project/<short_id> prefix;
  // null -> that request fails, a missing key falls back to `dashboard`.
  projectDashboards: Record<string, DashboardData | null>
  // PromQL passthrough keyed by the metric-name path segment; null mimics the
  // backend's 404 on an empty result (e.g. no GPU exporter), which is not the
  // same as an unreachable backend — tests for that override the route.
  monitoring: Record<string, number | null>
  notifications: KaapanaNotification[]
  pendingApplicationsCount: number
}

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  policyData: {
    endpoints_per_role: {
      admin: [{ path: '.*', methods: ['GET', 'POST', 'PUT', 'DELETE'] }],
    },
  },
  aiiUser: { id: '00000000-0000-0000-0000-000000000001', realm_roles: ['admin'] },
  projects: [
    { id: 1, name: 'admin', short_id: 'admin', role_name: 'admin' },
    { id: 2, name: 'lung-study', short_id: 'lung01', role_name: 'user' },
  ],
  dashboard: {
    metrics: { Patients: 12, Studies: 34, Series: 210 },
    histograms: {
      Modality: { items: { CT: 120, MR: 60, SEG: 30 } },
      'Patient Sex': { items: { M: 7, F: 5 } },
    },
  },
  // Only lung01 deviates from `dashboard`: proves a row shows its OWN counts
  // while the selected project keeps the histograms the detail dialog needs.
  projectDashboards: {
    lung01: { metrics: { Patients: 5, Studies: 9, Series: 40 }, histograms: {} },
  },
  monitoring: {
    cpu: 42,
    mem: 63,
    net: 3_200_000,
    gpu: 17,
    dicom_patients_total: 1200,
    dicom_studies_total: 3400,
    dicom_series_total: 21000,
  },
  notifications: [
    {
      id: 'n-1',
      topic: 'Workflows',
      title: 'Workflow finished',
      description: 'total-segmentator completed on dataset lung-ct',
      icon: 'mdi-check-circle',
      link: '/web/workflows/workflows',
      timestamp: new Date('2026-01-01T12:00:00Z'),
    },
  ],
  pendingApplicationsCount: 0,
}

// localStorage["settings"] the portal-ui shell seeds; landingPage drives the
// dashboard `names` payload, so tests can assert against it.
export const defaultSettings = {
  darkMode: false,
  landingPage: ['Patient Sex', 'Modality'],
}

// Path the view is served under standalone (vite `base` / router history base).
export const UNSCOPED_VIEW_PATH = '/home-ui/'

export const defaultProject = defaultMockData.projects[0]

/** Document path the shell serves the view under, scoped to `project`. */
export function viewPathFor(project: { id: number; short_id?: string }): string {
  return `/project/${project.short_id ?? project.id}${UNSCOPED_VIEW_PATH}`
}

export const VIEW_PATH = viewPathFor(defaultProject)

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

/**
 * Intercept every backend call the home view makes so it boots without a
 * platform. Call before page.goto(). Override parts per test via `data`.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  // Prod/preview build asks the oauth2 proxy, the dev server a static token file.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))

  await page.route('**/kaapana-backend/open-policy-data', (r) => r.fulfill(json(data.policyData)))

  await page.route('**/aii/users/current', (r) => r.fulfill(json(data.aiiUser)))
  // The all-projects admin listing carries NO membership role in production
  // (only /aii/users/{id}/projects does) — strip it so the fixture cannot make
  // a missing role_name look present. base-ui patches it back in for admins.
  await page.route('**/aii/projects', (r) =>
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    r.fulfill(json(data.projects.map(({ role_name, ...rest }) => rest))),
  )
  await page.route('**/aii/users/*/projects', (r) => r.fulfill(json(data.projects)))

  await page.route('**/kaapana-backend/dataset/dashboard', (r) => {
    const slug = new URL(r.request().url()).pathname.match(/^\/project\/([^/]+)\//)?.[1]
    const perProject = slug ? data.projectDashboards[slug] : undefined
    if (perProject === null) return r.fulfill({ status: 500, body: '' })
    return r.fulfill(json(perProject ?? data.dashboard))
  })

  await page.route('**/kaapana-backend/monitoring/query/*', (r) => {
    const name = decodeURIComponent(new URL(r.request().url()).pathname.split('/').pop()!)
    const value = data.monitoring[name]
    if (value === null || value === undefined) {
      return r.fulfill({ status: 404, body: '' })
    }
    return r.fulfill(json({ metric: name, value, timestamp: '2026-01-01T12:00:00Z' }))
  })

  // Range variant feeds the sparklines: synthesize a series around the instant value.
  await page.route('**/kaapana-backend/monitoring/query-range/*', (r) => {
    const name = decodeURIComponent(new URL(r.request().url()).pathname.split('/').pop()!)
    const value = data.monitoring[name]
    if (value === null || value === undefined) {
      return r.fulfill({ status: 404, body: '' })
    }
    const points = Array.from({ length: 40 }, (_, i) => ({
      metric: name,
      value: value * (0.5 + i / 80),
      timestamp: '2026-01-01T12:00:00Z',
    }))
    return r.fulfill(json(points))
  })

  await page.route('**/kube-helm-api/pending-applications-count', (r) =>
    r.fulfill(json({ count: data.pendingApplicationsCount })),
  )

  // Accept the websocket silently; tests that push events use
  // installNotificationSocket, which wins as the later registration.
  await page.routeWebSocket('**/notifications/ws', () => {})

  await page.route('**/notifications/v2/**', (r) => {
    if (r.request().method() === 'PUT') {
      const id = new URL(r.request().url()).pathname.split('/').at(-2)
      data.notifications = data.notifications.filter((n) => n.id !== id)
      return r.fulfill(json({}))
    }
    return r.fulfill(
      json({
        data: data.notifications,
        meta: { nextCursor: null, hasMore: false, total: data.notifications.length },
      }),
    )
  })
}

/**
 * Accept the notifications websocket. Returns a handle whose send() pushes a
 * server event ({id, type: 'new'|'read'}) into the page, like the
 * notification-service would.
 */
export async function installNotificationSocket(page: Page) {
  const handle: { send: (event: { id: string; type: 'new' | 'read' }) => void } = {
    send: () => {
      throw new Error('websocket not connected yet')
    },
  }
  await page.routeWebSocket('**/notifications/ws', (ws) => {
    handle.send = (event) => ws.send(JSON.stringify(event))
  })
  return handle
}

/**
 * Serve a marker page for the shell routes the view navigates the top window to
 * (workflow cards -> /web/..., another project -> /project/<short_id>), so the
 * navigation lands somewhere same-origin.
 */
export async function stubShellRoutes(page: Page) {
  const shell = (r: Route) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><html><body data-stub="shell">shell</body></html>' })
  await page.route('**/web/**', shell)
  await page.route('**/project/*/workflows/**', shell)
  // The shell's project home. One segment only, so it cannot swallow the
  // view's own /project/<short_id>/home-ui/ document.
  await page.route('**/project/*', shell)
}

/**
 * Seed localStorage["settings"] the way the portal-ui shell would before the view
 * loads. The project is NOT seeded — it travels in the document URL
 * (/project/<short_id>/...), see VIEW_PATH.
 */
export async function seedShellState(page: Page, settings: object = defaultSettings) {
  await page.addInitScript((s) => {
    localStorage.setItem('settings', s)
  }, JSON.stringify(settings))
}
