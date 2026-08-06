import type { Page } from '@playwright/test'

export const UNSCOPED_VIEW_PATH = '/federated-ui/'
// The /project/<short_id> document prefix IS the project selection
// (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/federated-ui/'

// The federated-ui backend contract. These shapes are declared inline
// (non-exported) in the app's KaapanaInstance.vue / AddRemoteInstance.vue setup
// scripts, so they cannot be imported; kept in sync here.
export interface RunnerInstance {
  id: number | string
  instance_name: string
  host: string
  port: number | string
  token: string
  fernet_key: string
  ssl_check: boolean
  remote: boolean
  time_created: number | string
  time_updated: number | string
  protocol?: string
  automatic_update?: boolean
  automatic_workflow_execution?: boolean
  allowed_dags?: string[]
  allowed_datasets?: { name: string; access_level?: string }[]
}

// Auth token payload consumed by useAuthStore in @kaapana/base-ui (reads .groups).
export interface UserinfoJwt {
  preferredUsername: string
  groups: string[]
  user: string
}

export interface Project {
  id: number
  name: string
  short_id: string
}

export interface MockData {
  userinfo: UserinfoJwt
  instances: RunnerInstance[]
  dags: string[]
  datasets: { name: string; access_level: string }[]
}

// The project VIEW_PATH scopes to, plus a second one so scoping tests can
// prove the slug (not a default) drives the API prefix.
export const defaultProject: Project = { id: 1, name: 'admin', short_id: 'admin' }
export const secondProject: Project = { id: 2, name: 'research-b', short_id: 'resb' }

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: Project): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

export const localInstance: RunnerInstance = {
  id: 1,
  instance_name: 'central-node',
  host: 'localhost',
  port: 443,
  token: 'local-token',
  fernet_key: 'deactivated',
  ssl_check: true,
  remote: false,
  protocol: 'https',
  time_created: '2024-01-01T00:00:00',
  time_updated: '2024-01-01T00:00:00',
  automatic_update: true,
  automatic_workflow_execution: false,
  allowed_dags: [],
  allowed_datasets: [],
}

export const remoteInstance: RunnerInstance = {
  id: 2,
  instance_name: 'gpu-node-1',
  host: '10.0.0.5',
  port: 443,
  token: 'remote-token',
  fernet_key: 'abc123',
  ssl_check: false,
  remote: true,
  protocol: 'https',
  time_created: '2024-01-01T00:00:00',
  time_updated: new Date().toISOString(),
  automatic_update: false,
  automatic_workflow_execution: false,
  allowed_dags: ['dag-a'],
  allowed_datasets: [],
}

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  instances: [localInstance, remoteInstance],
  dags: ['dag-a', 'dag-b'],
  datasets: [{ name: 'ds-project', access_level: 'project' }],
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

/**
 * Seed the shell-owned localStorage["settings"] before the view boots. The
 * project is NOT seeded — it travels in the document URL (/project/<short_id>/).
 */
export async function seedShellState(
  page: Page,
  settings: Record<string, unknown> = { darkMode: false },
) {
  await page.addInitScript((settings) => {
    localStorage.setItem('settings', JSON.stringify(settings))
  }, settings)
}

/**
 * Intercept every backend call the runner-instances view makes so it runs
 * without a platform. Call before page.goto(). Routes are matched by regex to
 * avoid the query-string/substring pitfalls of the near-identical paths; the
 * instance list is served from a mutable copy so create/delete flows see a
 * realistic refetch after their mutation.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  const instances: RunnerInstance[] = data.instances.map((i) => ({ ...i }))

  // Auth: dev server reads a static token file, prod build asks the oauth2 proxy.
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))

  await page.route(/\/client\/get-kaapana-instances/, (r) => r.fulfill(json(instances)))

  await page.route(/\/client\/check-for-remote-updates/, (r) => r.fulfill(json({})))

  await page.route(/\/client\/remote-kaapana-instance/, (r) => {
    if (r.request().method() === 'POST') {
      const body = r.request().postDataJSON() ?? {}
      instances.push({
        id: instances.length + 100,
        instance_name: body.instance_name,
        host: body.host,
        port: body.port,
        token: body.token,
        fernet_key: body.fernet_key ?? 'deactivated',
        ssl_check: !!body.ssl_check,
        remote: true,
        protocol: 'https',
        time_created: new Date().toISOString(),
        time_updated: new Date().toISOString(),
        allowed_dags: [],
        allowed_datasets: [],
      })
    }
    return r.fulfill(json({}))
  })

  await page.route(/\/client\/client-kaapana-instance/, (r) => r.fulfill(json({})))

  await page.route(/\/client\/kaapana-instance(\?|$)/, (r) => {
    if (r.request().method() === 'DELETE') {
      const id = new URL(r.request().url()).searchParams.get('kaapana_instance_id')
      const idx = instances.findIndex((i) => String(i.id) === String(id))
      if (idx !== -1) instances.splice(idx, 1)
      return r.fulfill(json({}))
    }
    return r.fulfill(json({ token: 'remote-token' }))
  })

  await page.route(/\/client\/get-dags/, (r) => r.fulfill(json(data.dags)))
  await page.route(/\/client\/datasets/, (r) => r.fulfill(json(data.datasets)))
}
