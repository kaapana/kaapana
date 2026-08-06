import type { BrowserContext, Page } from '@playwright/test'
import { settings as defaultUiSettings } from '../../../src/static/defaultUIConfig'

// Path the view is served under standalone (vite `base` / router history base).
export const UNSCOPED_VIEW_PATH = '/data-upload-ui/'
// Path the shell serves the view under: the /project/<short_id> document
// prefix IS the project selection (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/data-upload-ui/'

// The upload endpoint FilePond posts to (see components/Upload.vue default).
export const UPLOAD_URL = '/kaapana-backend/client/file'

// Minimal shapes mirroring what the view consumes (the app defines these
// inline, no exported types); kept narrow so contract drift shows in the specs.
export interface Project {
  id: number
  name: string
  short_id: string
  is_archived?: boolean
}

export interface Userinfo {
  preferredUsername: string
  groups: string[]
  user: string
}

export interface AiiCurrentUser {
  id: string
  realm_roles: string[]
}

export interface KaapanaInstance {
  instance_name: string
  remote: boolean
  allowed_dags: string[]
}

// Everything the data-upload view fetches, in one overridable bundle.
export interface MockData {
  userinfo: Userinfo
  currentUser: AiiCurrentUser
  projects: Project[]
  // Import dialog (WorkflowExecution): instances, importable dags, vjsf schemas.
  instances: KaapanaInstance[]
  dags: string[]
  schemas: Record<string, Record<string, any>>
}

const IMPORT_DAG = 'import-dicoms-to-pacs'

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  currentUser: {
    id: '00000000-0000-0000-0000-000000000001',
    realm_roles: ['admin'],
  },
  projects: [
    { id: 1, name: 'admin', short_id: 'admin' },
    { id: 2, name: 'research-b', short_id: 'resb' },
  ],
  instances: [
    { instance_name: 'kaapana-local', remote: false, allowed_dags: [IMPORT_DAG] },
  ],
  dags: [IMPORT_DAG],
  schemas: {
    // One dag + a matching schema key so the two cross-gating watchers in
    // WorkflowExecution auto-select `dag_id`. No `required` fields, so the
    // form submits without any user interaction.
    [IMPORT_DAG]: {
      workflow_form: {
        type: 'object',
        title: 'Workflow Form',
        properties: {
          single_execution: { type: 'boolean', title: 'Single execution', default: false },
        },
      },
    },
  },
}

// data_form with the dataset_name oneOf + dataset_limit, which WorkflowExecution
// lifts out of vjsf into a native autocomplete and a whole-dataset toggle.
// dataset_name is deliberately not required, so submit is not gated on a choice.
export const DATASET_IMPORT_DAG = 'import-dicoms-with-dataset'
export function datasetImportData(): MockData {
  return {
    ...defaultMockData,
    instances: [{ instance_name: 'kaapana-local', remote: false, allowed_dags: [DATASET_IMPORT_DAG] }],
    dags: [DATASET_IMPORT_DAG],
    schemas: {
      [DATASET_IMPORT_DAG]: {
        workflow_form: {
          type: 'object',
          properties: {
            single_execution: { type: 'boolean', title: 'Single execution', default: false },
          },
        },
        data_form: {
          type: 'object',
          properties: {
            dataset_name: {
              type: 'string',
              title: 'Dataset name (size)',
              oneOf: [
                { const: { name: 'nsclc', username: 'kaapana', access_level: 'project' }, title: 'nsclc (project) (42)' },
                { const: { name: 'brains', username: 'kaapana', access_level: 'project' }, title: 'brains (project) (7)' },
              ],
            },
            dataset_limit: {
              type: 'integer',
              title: 'Limit dataset size',
              description: 'Limit dataset to this many cases.',
            },
          },
        },
      },
    },
  }
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

/** The project VIEW_PATH scopes to (the store resolves the URL slug against the list). */
export function selectedProjectOf(data: MockData): Project {
  return data.projects[0]
}

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: Project): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

/**
 * Seed the same-origin state the portal-ui shell writes before an embedded
 * view boots: localStorage["settings"] (the UI-config object). The project is
 * NOT seeded — it travels in the document URL (/project/<short_id>/...).
 */
export async function seedShellState(context: BrowserContext) {
  await context.addInitScript((s) => {
    localStorage.setItem('settings', s)
  }, JSON.stringify(defaultUiSettings))
}

/**
 * Intercept every backend call the view makes so it boots without a platform.
 * Call before page.goto(). Later page.route overrides win — add error-response
 * routes after this call.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  await seedShellState(page.context())

  // The router guard proceeds even on auth failure (the gateway is the real
  // boundary); these only shape the logged-in vs logged-out view.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))

  // Project store (admin path hits /aii/projects; non-admin the per-user list).
  await page.route('**/aii/users/current', (r) => r.fulfill(json(data.currentUser)))
  await page.route('**/aii/projects', (r) => r.fulfill(json(data.projects)))
  await page.route(`**/aii/users/${data.currentUser.id}/projects`, (r) =>
    r.fulfill(json(data.projects)),
  )

  // FilePond chunked upload: POST returns a plain-text transfer id (the ?patch=
  // id), PATCH acks each chunk, DELETE reverts, HEAD is the resume probe.
  await page.route(/\/kaapana-backend\/client\/file(\?|$)/, (r) => {
    const method = r.request().method()
    if (method === 'POST') {
      return r.fulfill({ status: 200, contentType: 'text/plain', body: 'mock-transfer-id' })
    }
    if (method === 'HEAD') {
      return r.fulfill({ status: 200, headers: { 'Upload-Offset': '0' } })
    }
    return r.fulfill({ status: 200, contentType: 'text/plain', body: '' })
  })

  // Import dialog (WorkflowExecution) client endpoints.
  await page.route('**/kaapana-backend/client/get-kaapana-instances', (r) =>
    r.fulfill(json(data.instances)),
  )
  await page.route('**/kaapana-backend/client/get-dags', (r) => r.fulfill(json(data.dags)))
  await page.route('**/kaapana-backend/client/get-ui-form-schemas', (r) =>
    r.fulfill(json(data.schemas)),
  )
  await page.route('**/kaapana-backend/client/workflow', (r) => r.fulfill(json({ workflow_id: 'wf-1' })))
}
