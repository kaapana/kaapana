import type { Page, Route } from '@playwright/test'
import type { Workflow, Job, KaapanaInstance } from '../../../src/types/workflow'

export const UNSCOPED_VIEW_PATH = '/workflow-list-ui/'
// The /project/<short_id> document prefix IS the project selection
// (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/workflow-list-ui/'

// This view has no project store — the /project/<short_id>/ document prefix
// alone scopes its API calls — so projects exist here only as URL slugs.
export const PROJECT_SLUGS = ['admin', 'resb']

/** Shell URL of the view scoped to the project `slug` (see VIEW_PATH). */
export function viewPathFor(slug: string): string {
  return `/project/${slug}${UNSCOPED_VIEW_PATH}`
}

// The auth store only reads `preferredUsername`, `groups` (must be an array —
// it calls .filter), and `user`.
interface Userinfo {
  preferredUsername: string
  groups: string[]
  user: string
}

// Everything this view fetches, in one overridable bundle. Shapes are imported
// from the app source so contract drift fails type-check.
export interface MockData {
  userinfo: Userinfo
  // response.data of GET /kaapana-backend/client/kaapana-instance (getLocalInstance)
  localInstance: KaapanaInstance
  // GET /kaapana-backend/client/workflows returns the tuple [rows, totalCount]
  workflows: Workflow[]
  totalWorkflows: number
  // GET /kaapana-backend/client/jobs returns Job[] (jobs of the expanded workflow)
  jobs: Job[]
}

const localInstance: KaapanaInstance = { instance_name: 'local', remote: false }

// A representative mix of states; the field combos drive which action buttons
// render (see WorkflowTable.vue). `workflow_jobs` is a string[] of per-job
// statuses feeding the status-chip counts, separate from `status`.
const workflows: Workflow[] = [
  {
    workflow_name: 'running-wf',
    workflow_id: 'wf-running-001',
    dataset_name: { name: 'ct-scans', access_level: 'public' },
    time_created: '2026-07-20T10:00:00',
    time_updated: '2026-07-20T10:05:00',
    username: 'kaapana',
    kaapana_instance: localInstance,
    status: 'running',
    service_workflow: false,
    automatic_execution: true,
    workflow_jobs: ['running', 'running', 'finished'],
  },
  {
    workflow_name: 'finished-wf',
    workflow_id: 'wf-finished-002',
    dataset_name: { name: 'mr-scans', access_level: 'private' },
    time_created: '2026-07-19T09:00:00',
    time_updated: '2026-07-19T09:30:00',
    username: 'kaapana',
    kaapana_instance: localInstance,
    status: 'finished',
    service_workflow: false,
    automatic_execution: true,
    workflow_jobs: ['finished', 'finished', 'finished'],
  },
  {
    workflow_name: 'failed-wf',
    workflow_id: 'wf-failed-003',
    dataset_name: null,
    time_created: '2026-07-18T08:00:00',
    time_updated: '2026-07-18T08:15:00',
    username: 'kaapana',
    kaapana_instance: localInstance,
    status: 'failed',
    service_workflow: false,
    automatic_execution: true,
    workflow_jobs: ['failed', 'finished'],
  },
  {
    workflow_name: 'queued-wf',
    workflow_id: 'wf-queued-004',
    dataset_name: null,
    time_created: '2026-07-17T07:00:00',
    time_updated: '2026-07-17T07:01:00',
    username: 'kaapana',
    kaapana_instance: localInstance,
    status: 'queued',
    service_workflow: false,
    automatic_execution: false,
    workflow_jobs: ['queued', 'scheduled', 'pending'],
  },
]

// Jobs of the expanded workflow. instance_name === owner_kaapana_instance_name
// so the local job action buttons (abort/restart/delete) render.
const jobs: Job[] = [
  {
    id: 101,
    status: 'running',
    description: "{'op-a': {'state': 'running', 'start_date': '2026-07-20T10:01:00'}}",
    conf_data: { workflow_form: { input: 'ct-scans' } },
    time_created: '2026-07-20T10:00:30',
    time_updated: '2026-07-20T10:04:00',
    dag_id: 'dag-alpha',
    run_id: 'run-alpha-20260720100000',
    kaapana_instance: localInstance,
    owner_kaapana_instance_name: 'local',
    external_job_id: null,
    service_job: false,
  },
  {
    id: 102,
    status: 'failed',
    description: "{'op-b': {'state': 'failed', 'start_date': '2026-07-20T10:02:00'}}",
    conf_data: { workflow_form: { input: 'ct-scans' } },
    time_created: '2026-07-20T10:00:40',
    time_updated: '2026-07-20T10:03:00',
    dag_id: 'dag-beta',
    run_id: 'run-beta-20260720100000',
    kaapana_instance: localInstance,
    owner_kaapana_instance_name: 'local',
    external_job_id: null,
    service_job: false,
  },
]

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  localInstance,
  workflows,
  totalWorkflows: workflows.length,
  jobs,
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

const CLIENT = '/kaapana-backend/client'

/**
 * Seed the shell-owned localStorage["settings"] before the view boots. The
 * project is NOT seeded — it travels in the document URL (/project/<short_id>/).
 */
export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
  })
}

/**
 * Intercept every backend call this view makes so it boots without a platform.
 * Call before page.goto(); add per-test page.route() overrides AFTER this call
 * (later routes win in Playwright). Settings are seeded by default, as the
 * shell does; `seedSettings: false` opts out so the unseeded-boot regression
 * stays testable (see workflow-list.spec.ts).
 */
export async function installMockBackend(
  page: Page,
  data: MockData = defaultMockData,
  options: { seedSettings?: boolean } = {},
) {
  if (options.seedSettings !== false) await seedShellState(page)

  // Auth: prod build asks the oauth2 proxy, dev server a static token file.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))

  await page.route(new RegExp(`${CLIENT}/kaapana-instance(\\?|$)`), (r) =>
    r.fulfill(json(data.localInstance)),
  )

  await page.route(new RegExp(`${CLIENT}/workflows(\\?|$)`), (r) =>
    r.fulfill(json([data.workflows, data.totalWorkflows])),
  )

  await page.route(new RegExp(`${CLIENT}/jobs(\\?|$)`), (r) => r.fulfill(json(data.jobs)))

  await page.route(new RegExp(`${CLIENT}/check-for-remote-updates`), (r) => r.fulfill(json({})))

  await page.route(new RegExp(`${CLIENT}/get-job-taskinstances`), (r) => r.fulfill(json({})))

  await page.route(new RegExp(`${CLIENT}/workflow(\\?|$)`), (r: Route) => r.fulfill(json({})))

  await page.route(new RegExp(`${CLIENT}/job(\\?|$)`), (r: Route) => r.fulfill(json({})))
}
