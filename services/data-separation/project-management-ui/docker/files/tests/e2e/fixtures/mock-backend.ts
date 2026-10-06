import type { Page, Route } from '@playwright/test'
import type { PolicyData } from '@kaapana/base-ui'
import type { ProjectItem, UserItem } from '@/common/types'
import type { UserRight } from '@/permissions/permissions.store'

// The vite `base`. The shell embeds this view without a /project/<short_id> prefix.
export const VIEW_PATH = '/projects-ui/'

export function projectPath(project: ProjectItem): string {
  return `${VIEW_PATH}project/${project.id}`
}

// Shapes the app reads without declaring a type for them in src/, re-derived
// from the backend schemas: AII projects/schemas.py and kube-helm schemas.py.

export interface Role {
  id: number
  name: string
  description: string
}

export interface Right {
  id: number
  name: string
  description: string
  claim_key: string
  claim_value: string
}

export interface ExtensionParam {
  type: 'string' | 'bool' | 'boolean' | 'list_single' | 'list_multi' | 'group_name' | 'doc'
  default?: unknown
  definition?: string
  value?: string[]
  help?: string
  title?: string
  html?: string
}

export interface ExtensionMock {
  releaseName: string
  name: string
  version: string
  keywords: string[]
  multiinstallable: 'yes' | 'no'
  installed: 'yes' | 'no'
  description?: string
  helmStatus?: string
  annotations: Record<string, string>
  extension_params?: Record<string, ExtensionParam>
}

export interface ActiveApplicationMock {
  name: string
  namespace: string
  project: string
  release_name: string
  paths: string[]
  ready: boolean
  annotations: Record<string, string>
  values?: Record<string, unknown>
}

export interface Membership {
  userId: string
  role: string
}

export interface MockData {
  /** GET /kaapana-backend/open-policy-data: the role grants of the gateway. */
  policyData: PolicyData
  currentUser: UserItem
  /** The current user's AII rights, across all projects. */
  rights: UserRight[]
  projects: ProjectItem[]
  /** Every realm user, as GET /aii/users lists them. */
  users: UserItem[]
  /** Project id -> members with their project role. */
  members: Record<string, Membership[]>
  roles: Role[]
  rightsCatalogue: Right[]
  /** Role id -> right ids granted to it. */
  roleRights: Record<number, number[]>
  /** Project id -> allowed workflow (DAG) ids. */
  softwareMappings: Record<string, string[]>
  /** Project id -> allowed multi-installable application names. */
  whitelists: Record<string, string[]>
  dags: string[]
  extensions: ExtensionMock[]
  activeApplications: ActiveApplicationMock[]
}

export const ADMIN_PROJECT: ProjectItem = {
  id: '00000000-0000-0000-0000-00000000a001',
  short_id: 'admin',
  name: 'admin',
  description: 'Default project of the platform administrators',
  external_id: null,
  is_archived: false,
}

export const RESEARCH_PROJECT: ProjectItem = {
  id: '5e7a9c1b-0000-0000-0000-00000000b002',
  short_id: '5e7a9c1b',
  name: 'lung-study',
  description: 'Lung nodule segmentation study',
  external_id: 'EXT-42',
  is_archived: false,
}

export const ADMIN_USER: UserItem = {
  id: '00000000-0000-0000-0000-000000000001',
  username: 'kaapana',
  first_name: 'Kaapana',
  last_name: 'Admin',
  email: 'kaapana@example.org',
  email_verified: true,
  realm_roles: ['admin', 'project-manager', 'user'],
}

export const SCIENTIST_USER: UserItem = {
  id: '00000000-0000-0000-0000-000000000002',
  username: 'ada',
  first_name: 'Ada',
  last_name: 'Lovelace',
  email: 'ada@example.org',
  email_verified: true,
  realm_roles: ['user'],
}

export const CANDIDATE_USER: UserItem = {
  id: '00000000-0000-0000-0000-000000000003',
  username: 'alan',
  first_name: 'Alan',
  last_name: 'Turing',
  email: 'alan@example.org',
  email_verified: true,
  realm_roles: ['user'],
}

export const SYSTEM_USER: UserItem = {
  id: '00000000-0000-0000-0000-000000000004',
  username: 'kaapana-system-user',
  first_name: 'Kaapana',
  last_name: 'system',
  email: '',
  email_verified: false,
  realm_roles: ['admin'],
}

// The role grants of auth-backend's data.rego that this view's controls
// depend on.
export const defaultPolicyData: PolicyData = {
  endpoints_per_role: {
    user: [
      { path: '^/aii/.*', methods: ['GET'] },
      { path: '^/kube-helm-api/active-applications', methods: ['GET'] },
      { path: '^/projects-ui.*', methods: ['GET'] },
    ],
    'project-manager': [
      { path: '^/aii/.*', methods: ['GET', 'POST', 'PUT', 'DELETE'] },
      { path: '^/projects-ui.*', methods: ['GET', 'POST', 'PUT', 'DELETE'] },
      { path: '^/kaapana-backend/open-policy-data', methods: ['GET'] },
    ],
    admin: [{ path: '^/.*', methods: ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'PATCH'] }],
  },
}

export const defaultMockData: MockData = {
  policyData: defaultPolicyData,
  currentUser: ADMIN_USER,
  rights: [],
  projects: [ADMIN_PROJECT, RESEARCH_PROJECT],
  users: [ADMIN_USER, SCIENTIST_USER, CANDIDATE_USER, SYSTEM_USER],
  members: {
    [ADMIN_PROJECT.id]: [
      { userId: ADMIN_USER.id, role: 'admin' },
      { userId: SYSTEM_USER.id, role: 'admin' },
    ],
    [RESEARCH_PROJECT.id]: [
      { userId: ADMIN_USER.id, role: 'admin' },
      { userId: SCIENTIST_USER.id, role: 'scientist' },
    ],
  },
  roles: [
    { id: 1, name: 'admin', description: 'Administers the project' },
    { id: 2, name: 'principal-investigator', description: 'Leads the project' },
    { id: 3, name: 'scientist', description: 'Works with approved software' },
  ],
  rightsCatalogue: [
    {
      id: 1,
      name: 'manage_users',
      description: 'Add and remove project members',
      claim_key: 'kaapana.ai/aii',
      claim_value: 'manage_users',
    },
    {
      id: 2,
      name: 'launch_application',
      description: 'Launch whitelisted applications',
      claim_key: 'kaapana.ai/applications',
      claim_value: 'launch',
    },
  ],
  roleRights: { 1: [1, 2], 2: [1, 2], 3: [2] },
  softwareMappings: { [RESEARCH_PROJECT.id]: ['collect-metadata'] },
  whitelists: { [RESEARCH_PROJECT.id]: [] },
  dags: ['collect-metadata', 'nnunet-predict', 'total-segmentator'],
  extensions: [
    {
      releaseName: 'jupyterlab',
      name: 'jupyterlab',
      version: '4.2.0',
      keywords: ['kaapana-application'],
      multiinstallable: 'yes',
      installed: 'no',
      description: 'Interactive notebook environment for data exploration',
      annotations: { 'ui-visible-name': 'JupyterLab', documentation: 'jupyterlab' },
      extension_params: {
        workspace_name: {
          type: 'string',
          default: 'notebooks',
          definition: 'Workspace name',
          help: 'Folder created in the project bucket.',
        },
      },
    },
    {
      releaseName: 'tensorboard',
      name: 'tensorboard',
      version: '2.17.0',
      keywords: ['kaapana-application'],
      multiinstallable: 'yes',
      installed: 'no',
      description: 'Training metrics dashboard',
      annotations: { 'ui-visible-name': 'Tensorboard', documentation: 'tensorboard' },
    },
    {
      releaseName: 'jupyterlab-a1b2c',
      name: 'jupyterlab',
      version: '4.2.0',
      keywords: ['kaapana-application'],
      multiinstallable: 'yes',
      installed: 'yes',
      helmStatus: 'deployed',
      description: 'Interactive notebook environment for data exploration',
      annotations: { 'ui-visible-name': 'JupyterLab' },
    },
  ],
  activeApplications: [
    {
      name: 'jupyterlab',
      namespace: 'project-5e7a9c1b',
      project: RESEARCH_PROJECT.id,
      release_name: 'jupyterlab-a1b2c',
      paths: ['/applications/project/5e7a9c1b/release/jupyterlab-a1b2c'],
      ready: true,
      annotations: { 'kaapana.ai/display-name': 'JupyterLab (notebooks)' },
      values: {
        extension_params: { workspace_name: { default: 'notebooks', value: 'notebooks' } },
      },
    },
  ],
}

function json(body: unknown, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(body) }
}

function notFound(route: Route, method: string, path: string) {
  return route.fulfill(json({ detail: `mock backend: no handler for ${method} ${path}` }, 404))
}

/** The path below the first /aii/ segment: /aii/aii/users/x -> /aii/users/x. */
function aiiPath(url: string): string {
  const path = new URL(url).pathname
  return path.slice(path.indexOf('/aii/') + '/aii'.length)
}

function newProjectId(state: MockData): string {
  const hex = (state.projects.length + 1).toString(16).padStart(8, 'c')
  return `${hex}-0000-0000-0000-000000000000`
}

function projectsOf(state: MockData, userId: string): ProjectItem[] {
  return state.projects.filter((p) => state.members[p.id]?.some((m) => m.userId === userId))
}

function handleAii(route: Route, state: MockData) {
  const request = route.request()
  const method = request.method()
  const path = aiiPath(request.url())
  const body = () => request.postDataJSON()
  let m: RegExpMatchArray | null

  if (method === 'GET' && path === '/users/current') return route.fulfill(json(state.currentUser))
  if (method === 'GET' && path === '/users') return route.fulfill(json(state.users))
  if (method === 'GET' && (m = path.match(/^\/users\/([^/]+)\/projects$/)))
    return route.fulfill(json(projectsOf(state, m[1])))
  if (method === 'GET' && /^\/aii\/users\/[^/]+\/rights$/.test(path))
    return route.fulfill(json(state.rights))

  // Before /projects/<id>, which would also match /projects/roles and /projects/rights.
  if (method === 'GET' && path === '/projects/roles') return route.fulfill(json(state.roles))
  if (path === '/projects/rights') {
    if (method === 'GET') return route.fulfill(json(state.rightsCatalogue))
    if (method === 'POST') {
      const right: Right = {
        id: Math.max(0, ...state.rightsCatalogue.map((r) => r.id)) + 1,
        ...body(),
      }
      state.rightsCatalogue.push(right)
      return route.fulfill(json(right))
    }
  }
  if (method === 'POST' && path === '/projects/rights/reset')
    return route.fulfill(json({ reset: Object.values(state.roleRights).flat().length }))
  if (method === 'DELETE' && (m = path.match(/^\/projects\/rights\/(\d+)$/))) {
    const id = Number(m[1])
    state.rightsCatalogue = state.rightsCatalogue.filter((r) => r.id !== id)
    return route.fulfill({ status: 204 })
  }
  if (method === 'GET' && (m = path.match(/^\/projects\/roles\/(\d+)\/rights$/))) {
    const granted = state.roleRights[Number(m[1])] ?? []
    return route.fulfill(json(state.rightsCatalogue.filter((r) => granted.includes(r.id))))
  }
  if ((m = path.match(/^\/projects\/roles\/(\d+)\/rights\/(\d+)$/))) {
    const [roleId, rightId] = [Number(m[1]), Number(m[2])]
    const granted = new Set(state.roleRights[roleId] ?? [])
    if (method === 'POST') granted.add(rightId)
    if (method === 'DELETE') granted.delete(rightId)
    state.roleRights[roleId] = [...granted]
    return route.fulfill(method === 'DELETE' ? { status: 204 } : json({}))
  }

  if (path === '/projects') {
    if (method === 'GET') return route.fulfill(json(state.projects))
    if (method === 'POST') {
      const id = newProjectId(state)
      const project: ProjectItem = {
        id,
        short_id: id.slice(0, 8),
        is_archived: false,
        ...body(),
      }
      state.projects.push(project)
      state.members[id] = [{ userId: state.currentUser.id, role: 'admin' }]
      return route.fulfill(json(project))
    }
  }
  if ((m = path.match(/^\/projects\/([^/]+)$/))) {
    const project = state.projects.find((p) => p.id === m![1])
    if (!project) return route.fulfill(json({ detail: 'Project not found' }, 404))
    if (method === 'GET') return route.fulfill(json(project))
    if (method === 'PUT') {
      Object.assign(project, body())
      return route.fulfill(json(project))
    }
    if (method === 'DELETE') {
      state.projects = state.projects.filter((p) => p !== project)
      return route.fulfill({ status: 204 })
    }
  }
  if (method === 'POST' && (m = path.match(/^\/projects\/([^/]+)\/(archive|unarchive)$/))) {
    const project = state.projects.find((p) => p.id === m![1])!
    project.is_archived = m[2] === 'archive'
    return route.fulfill(json(project))
  }

  if (method === 'GET' && (m = path.match(/^\/projects\/([^/]+)\/users$/))) {
    const ids = (state.members[m[1]] ?? []).map((x) => x.userId)
    return route.fulfill(json(state.users.filter((u) => ids.includes(u.id))))
  }
  if (method === 'GET' && (m = path.match(/^\/projects\/([^/]+)\/users\/([^/]+)\/roles$/))) {
    const membership = state.members[m[1]]?.find((x) => x.userId === m![2])
    const role = state.roles.find((r) => r.name === membership?.role)
    return role ? route.fulfill(json(role)) : route.fulfill({ status: 204 })
  }
  if (
    method === 'POST' &&
    (m = path.match(/^\/projects\/([^/]+)\/role\/([^/]+)\/user\/([^/]+)$/))
  ) {
    ;(state.members[m[1]] ??= []).push({ userId: m[3], role: m[2] })
    return route.fulfill(json({}))
  }
  if ((m = path.match(/^\/projects\/([^/]+)\/user\/([^/]+)\/rolemapping$/))) {
    const [projectId, userId] = [m[1], m[2]]
    if (method === 'PUT') {
      const roleName = new URL(request.url()).searchParams.get('role_name')!
      state.members[projectId].find((x) => x.userId === userId)!.role = roleName
      return route.fulfill(json({}))
    }
    if (method === 'DELETE') {
      state.members[projectId] = state.members[projectId].filter((x) => x.userId !== userId)
      return route.fulfill({ status: 204 })
    }
  }

  if ((m = path.match(/^\/projects\/([^/]+)\/software-mappings$/))) {
    const projectId = m[1]
    const current = new Set(state.softwareMappings[projectId] ?? [])
    if (method === 'POST') for (const s of body()) current.add(s.software_uuid)
    if (method === 'DELETE') for (const s of body()) current.delete(s.software_uuid)
    state.softwareMappings[projectId] = [...current]
    return route.fulfill(json([...current].map((software_uuid) => ({ software_uuid }))))
  }
  if ((m = path.match(/^\/projects\/([^/]+)\/multiinstallable-whitelist$/))) {
    if (method === 'PUT') state.whitelists[m[1]] = body().app_names
    return route.fulfill(json(state.whitelists[m[1]] ?? []))
  }

  return notFound(route, method, path)
}

function handleKubeHelm(route: Route, state: MockData) {
  const request = route.request()
  const method = request.method()
  const path = new URL(request.url()).pathname.replace(/^.*\/kube-helm-api/, '')

  if (method === 'GET' && path === '/extensions') return route.fulfill(json(state.extensions))
  if (method === 'GET' && path === '/active-applications')
    return route.fulfill(json(state.activeApplications))
  if (method === 'POST' && path === '/helm-install-chart') {
    // The launched instance runs in the project of the /project/<short_id> prefix.
    const slug = new URL(request.url()).pathname.match(/^\/project\/([^/]+)\//)?.[1]
    const project = state.projects.find((p) => p.short_id === slug)
    const { name } = request.postDataJSON()
    if (project) {
      state.activeApplications.push({
        name,
        namespace: `project-${project.short_id}`,
        project: project.id,
        release_name: `${name}-launched`,
        paths: [],
        ready: false,
        annotations: { 'kaapana.ai/display-name': `${name} (launched)` },
      })
    }
    return route.fulfill(json({}))
  }
  if (method === 'POST' && path === '/helm-delete-chart') {
    const { release_name } = request.postDataJSON()
    state.activeApplications = state.activeApplications.filter(
      (a) => a.release_name !== release_name,
    )
    return route.fulfill(json({}))
  }
  return notFound(route, method, path)
}

/**
 * Seed the same-origin state the portal-ui shell writes before an embedded
 * view boots: localStorage["settings"].
 */
export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
  })
}

/**
 * Intercept every backend call the view makes so it boots without a platform,
 * and seed the shell settings. Call before page.goto(). The backend works on
 * a copy of `data`, which it returns: mutations (create, delete, whitelist
 * saves, ...) change that copy, so a reload shows them and a test can assert
 * on it. Later page.route overrides win.
 *
 * `seedSettings: false` lets a test observe a fresh-profile boot, which
 * unconditional seeding would make the suite blind to.
 */
export async function installMockBackend(
  page: Page,
  data: MockData = defaultMockData,
  { seedSettings = true }: { seedSettings?: boolean } = {},
): Promise<MockData> {
  const state = structuredClone(data)
  if (seedSettings) await seedShellState(page)

  await page.route(/\/aii\//, (r) => handleAii(r, state))
  await page.route(/\/kube-helm-api\//, (r) => handleKubeHelm(r, state))
  await page.route('**/kaapana-backend/open-policy-data', (r) => r.fulfill(json(state.policyData)))
  await page.route(/\/kaapana-backend\/client\/dags(\?.*)?$/, (r) => r.fulfill(json(state.dags)))
  return state
}
