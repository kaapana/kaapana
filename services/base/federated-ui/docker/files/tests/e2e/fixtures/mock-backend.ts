import type { Page } from '@playwright/test'
import type { DatasetOption, KaapanaInstance } from '../../../src/api/federation'

export type { KaapanaInstance }

export const UNSCOPED_VIEW_PATH = '/federated-ui/'
export const VIEW_PATH = '/project/admin/federated-ui/'

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
  instances: KaapanaInstance[]
  dags: string[]
  datasets: DatasetOption[]
}

export const defaultProject: Project = { id: 1, name: 'admin', short_id: 'admin' }
export const secondProject: Project = { id: 2, name: 'research-b', short_id: 'resb' }

export function viewPathFor(project: Project): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

export const localInstance: KaapanaInstance = {
  id: 1,
  instance_name: 'central-node',
  host: 'localhost',
  port: 443,
  token: 'local-token',
  fernet_key: 'deactivated',
  ssl_check: true,
  remote: false,
  protocol: 'https',
  time_created: '2024-01-01T00:00:00+00:00',
  time_updated: '2024-01-01T00:00:00+00:00',
  automatic_update: true,
  automatic_workflow_execution: false,
  allowed_dags: [],
  allowed_datasets: [],
}

export const remoteInstance: KaapanaInstance = {
  id: 2,
  instance_name: 'gpu-node-1',
  host: '10.0.0.5',
  port: 443,
  token: 'remote-token',
  fernet_key: 'abc123',
  ssl_check: false,
  remote: true,
  protocol: 'https',
  time_created: '2024-01-01T00:00:00+00:00',
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
  datasets: [
    { name: 'ds-project', access_level: 'project' },
    { name: 'ds-private', access_level: 'user' },
  ],
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

export async function seedShellState(
  page: Page,
  settings: Record<string, unknown> = { darkMode: false },
) {
  await page.addInitScript((settings) => {
    localStorage.setItem('settings', JSON.stringify(settings))
  }, settings)
}

export const CLIENT = {
  instances: /\/client\/get-kaapana-instances/,
  sync: /\/client\/check-for-remote-updates/,
  remote: /\/client\/remote-kaapana-instance/,
  local: /\/client\/client-kaapana-instance/,
  instance: /\/client\/kaapana-instance(\?|$)/,
  dags: /\/client\/get-dags/,
  datasets: /\/client\/datasets/,
} as const

export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  const instances: KaapanaInstance[] = data.instances.map((i) => ({ ...i }))

  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))

  await page.route(CLIENT.instances, (r) => r.fulfill(json(instances)))
  await page.route(CLIENT.sync, (r) => r.fulfill(json(['Federated backend is up and running!'])))

  await page.route(CLIENT.remote, (r) => {
    const body = r.request().postDataJSON() ?? {}
    if (r.request().method() === 'POST') {
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
        time_updated: '0001-01-01T00:00:00+00:00',
        automatic_update: false,
        automatic_workflow_execution: false,
        allowed_dags: [],
        allowed_datasets: [],
      })
    } else if (r.request().method() === 'PUT') {
      const existing = instances.find((i) => i.instance_name === body.instance_name)
      if (existing) Object.assign(existing, body)
    }
    return r.fulfill(json({}))
  })

  await page.route(CLIENT.local, (r) => {
    const body = r.request().postDataJSON() ?? {}
    const local = instances.find((i) => !i.remote)
    if (local) {
      Object.assign(local, {
        ssl_check: body.ssl_check,
        automatic_update: body.automatic_update,
        automatic_workflow_execution: body.automatic_workflow_execution,
        allowed_dags: body.allowed_dags,
        allowed_datasets: (body.allowed_datasets ?? []).map((name: string) => ({ name })),
      })
    }
    return r.fulfill(json({}))
  })

  await page.route(CLIENT.instance, (r) => {
    if (r.request().method() === 'DELETE') {
      const id = new URL(r.request().url()).searchParams.get('kaapana_instance_id')
      const idx = instances.findIndex((i) => String(i.id) === String(id))
      if (idx !== -1) instances.splice(idx, 1)
      return r.fulfill(json({ ok: true }))
    }
    return r.fulfill(json({ token: 'remote-token' }))
  })

  await page.route(CLIENT.dags, (r) => r.fulfill(json(data.dags)))
  await page.route(CLIENT.datasets, (r) => r.fulfill(json(data.datasets)))
}
