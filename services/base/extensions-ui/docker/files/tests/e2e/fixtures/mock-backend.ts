import type { Page } from '@playwright/test'

// Path the view is served under standalone (vite `base` / router history base).
export const UNSCOPED_VIEW_PATH = '/extensions-ui/'
// Path the shell serves the view under: the /project/<short_id> document
// prefix IS the project selection (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/extensions-ui/'

// The extensions-ui frontend is untyped (every API payload is `any`), so these
// mock shapes are re-derived from the kube-helm backend schema (schemas.py ::
// KaapanaExtension) — the fields the view actually reads. Keep them in sync.

export interface DeploymentMock {
  deployment_id: string
  helm_status: string
  kube_status: string | string[]
  links: string[]
  ready: boolean
}

export interface AvailableVersionMock {
  deployments: DeploymentMock[]
}

export interface ExtensionParam {
  type: 'string' | 'bool' | 'boolean' | 'list_single' | 'list_multi' | 'group_name' | 'doc'
  default?: any
  definition?: string
  value?: any[]
  help?: string
  title?: string
  html?: string
}

export interface ExtensionMock {
  releaseName: string
  name: string
  chart_name: string
  version: string
  versions: string[]
  available_versions: Record<string, AvailableVersionMock>
  multiinstallable: 'yes' | 'no'
  kind: 'dag' | 'application'
  experimental: 'yes' | 'no'
  resourceRequirement: 'cpu' | 'gpu'
  successful: string | null
  installed: string
  description: string
  display_name: string
  keywords: string[]
  links?: string[]
  annotations?: Record<string, string> | null
  latest_version?: string | null
  // Omit entirely for extensions that install without a config form. The
  // backend may also report param-less extensions as the literal string 'null'.
  extension_params?: Record<string, ExtensionParam> | 'null' | null
}

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

export interface AiiCurrentUser {
  id: string
  realm_roles: string[]
}

// GET /kaapana-backend/open-policy-data — the shape checkAuthR reads. The view
// hides the controls calling admin-only kube-helm endpoints (update-extensions,
// filepond-upload/import-container) when the roles here do not grant them.
export interface PolicyData {
  endpoints_per_role: Record<string, { path: string; methods: string[] }[]>
}

export interface MockData {
  userinfo: UserinfoJwt
  commonData: unknown
  policyData: PolicyData
  extensions: ExtensionMock[]
  currentUser: AiiCurrentUser
  projects: Project[]
}

const readyDeployment = (releaseName: string): DeploymentMock => ({
  deployment_id: releaseName,
  helm_status: 'deployed',
  kube_status: 'Running',
  links: [],
  ready: true,
})

export const defaultExtensions: ExtensionMock[] = [
  // Installed application, healthy -> "Uninstall" + ready.
  {
    releaseName: 'mitk-workbench-abc123',
    name: 'mitk-workbench',
    chart_name: 'mitk-workbench',
    version: '1.0.0',
    versions: ['1.0.0'],
    available_versions: {
      '1.0.0': { deployments: [readyDeployment('mitk-workbench-abc123')] },
    },
    multiinstallable: 'no',
    kind: 'application',
    experimental: 'no',
    resourceRequirement: 'cpu',
    successful: 'yes',
    installed: 'yes',
    description: 'Interactive image segmentation workbench',
    display_name: 'MITK Workbench',
    keywords: ['kaapana-application'],
    links: ['https://localhost/applications/mitk'],
    annotations: { documentation: 'mitk' },
    latest_version: '1.0.0',
  },
  // Not installed workflow WITH a config form; two versions selectable.
  {
    releaseName: 'nnunet-workflow',
    name: 'nnunet-workflow',
    chart_name: 'nnunet-workflow',
    version: '2.1.0',
    versions: ['2.1.0', '2.0.0'],
    available_versions: {
      '2.1.0': { deployments: [] },
      '2.0.0': { deployments: [] },
    },
    multiinstallable: 'no',
    kind: 'dag',
    experimental: 'no',
    resourceRequirement: 'gpu',
    successful: null,
    installed: 'no',
    description: 'Deep-learning segmentation training',
    display_name: 'nnU-Net Training',
    keywords: ['kaapana-workflow'],
    annotations: { documentation: 'nnunet' },
    latest_version: '2.1.0',
    extension_params: {
      workflow_name: { type: 'string', default: 'nnunet-run', definition: 'Workflow name' },
      enable_gpu: { type: 'bool', default: true, definition: 'Enable GPU' },
      model_type: {
        type: 'list_single',
        default: '3d_fullres',
        value: ['3d_fullres', '2d'],
        definition: 'Model type',
      },
    },
  },
  // Currently installing -> "Pending" state.
  {
    releaseName: 'code-server-pending',
    name: 'code-server',
    chart_name: 'code-server',
    version: '4.0.0',
    versions: ['4.0.0'],
    available_versions: { '4.0.0': { deployments: [] } },
    multiinstallable: 'no',
    kind: 'application',
    experimental: 'no',
    resourceRequirement: 'cpu',
    successful: 'pending',
    installed: 'no',
    description: 'VS Code in the browser',
    display_name: 'Code Server',
    keywords: ['kaapana-application'],
    latest_version: '4.0.0',
  },
  // Experimental -> hidden by the default (Stable-only) maturity filter.
  {
    releaseName: 'experimental-tool',
    name: 'experimental-tool',
    chart_name: 'experimental-tool',
    version: '0.1.0',
    versions: ['0.1.0'],
    available_versions: { '0.1.0': { deployments: [] } },
    multiinstallable: 'no',
    kind: 'application',
    experimental: 'yes',
    resourceRequirement: 'cpu',
    successful: null,
    installed: 'no',
    description: 'Bleeding-edge preview extension',
    display_name: 'Experimental Tool',
    keywords: [],
  },
  // Multi-installable, no config form -> "Launch"; two versions selectable.
  {
    releaseName: 'jupyterlab',
    name: 'jupyterlab',
    chart_name: 'jupyterlab',
    version: '3.2.0',
    versions: ['3.2.0', '3.1.0'],
    available_versions: {
      '3.2.0': { deployments: [] },
      '3.1.0': { deployments: [] },
    },
    multiinstallable: 'yes',
    kind: 'application',
    experimental: 'no',
    resourceRequirement: 'cpu',
    successful: null,
    installed: 'no',
    description: 'Interactive notebook environment',
    display_name: 'JupyterLab',
    keywords: ['kaapana-application'],
  },
]

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  commonData: {},
  policyData: {
    endpoints_per_role: {
      admin: [{ path: '.*', methods: ['GET', 'POST', 'PUT', 'DELETE'] }],
    },
  },
  extensions: defaultExtensions,
  currentUser: {
    id: '00000000-0000-0000-0000-000000000001',
    realm_roles: ['admin'],
  },
  projects: [
    { id: 1, name: 'admin', short_id: 'admin' },
    { id: 2, name: 'research-b', short_id: 'resb' },
  ],
}

function json(body: unknown, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(body) }
}

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: Project): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

/**
 * Seed the same-origin state the portal-ui shell writes before an embedded
 * view boots: localStorage["settings"]. The project is NOT seeded — it
 * travels in the document URL (/project/<short_id>/...).
 */
export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
  })
}

/**
 * Intercept every backend call the extensions-ui makes so it boots without a
 * platform, and seed the shell settings. Call before page.goto(). Override
 * parts via `data`; later page.route overrides win.
 *
 * `seedSettings: false` lets a test observe a fresh-profile boot, which
 * unconditional seeding would make the suite blind to.
 */
export async function installMockBackend(
  page: Page,
  data: MockData = defaultMockData,
  { seedSettings = true }: { seedSettings?: boolean } = {},
) {
  if (seedSettings) await seedShellState(page)

  // Prod build asks the oauth2 proxy, the dev server a static token file.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) =>
    r.fulfill(json(data.userinfo)),
  )
  await page.route('**/jsons/commonData.json', (r) => r.fulfill(json(data.commonData)))
  await page.route('**/kaapana-backend/open-policy-data', (r) => r.fulfill(json(data.policyData)))

  // Project store (admin path hits /aii/projects; non-admin the per-user list).
  await page.route('**/aii/users/current', (r) => r.fulfill(json(data.currentUser)))
  await page.route('**/aii/projects', (r) => r.fulfill(json(data.projects)))
  await page.route(`**/aii/users/${data.currentUser.id}/projects`, (r) =>
    r.fulfill(json(data.projects)),
  )

  await page.route(/\/kube-helm-api\/extensions(\?.*)?$/, (r) => r.fulfill(json(data.extensions)))
  await page.route('**/kube-helm-api/update-extensions', (r) => r.fulfill(json({})))
  await page.route('**/kube-helm-api/helm-install-chart', (r) => r.fulfill(json({})))
  await page.route('**/kube-helm-api/helm-delete-chart', (r) => r.fulfill(json({})))
  await page.route(/\/kube-helm-api\/import-container(\?.*)?$/, (r) => r.fulfill(json({})))

  // FilePond (Upload.vue) bypasses httpClient — hence the real file drop in
  // project-scope.spec.ts. The POST answers a plain-text transfer id as
  // filepond expects; the follow-up PATCH/HEAD chunk calls only must not fail.
  await page.route('**/kube-helm-api/filepond-upload*', (r) =>
    r.request().method() === 'POST'
      ? r.fulfill({ status: 200, contentType: 'text/plain', body: 'transfer-1' })
      : r.fulfill({ status: 204, headers: { 'Upload-Offset': '0' } }),
  )
}
