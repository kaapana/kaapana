import type { Page, Route } from '@playwright/test'
import type {
  Dataset,
  LogLine,
  Task,
  TaskRun,
  Workflow,
  WorkflowParameter,
  WorkflowRun,
  WorkflowRunCreate,
} from '../../../src/types/schemas'
import { TaskRunStatus, WorkflowRunStatus } from '../../../src/types/schemas'

// Path the shell serves the view under: the /project/<short_id> document
// prefix IS the project selection (vite.config.ts strips it like traefik).
export const PROJECT = 'admin'
export const VIEW_BASE = `/project/${PROJECT}/workflow-ui`
export const WORKFLOWS_PATH = `${VIEW_BASE}/workflows`
export const RUNS_PATH = `${VIEW_BASE}/runs`
export const logsPath = (runId: number) => `${VIEW_BASE}/runs/${runId}/logs`

// Mock shapes are the app's own src/types/schemas.ts types, so a contract
// change fails the type-check of this suite.
export interface MockData {
  workflows: Workflow[]
  /** Tasks per workflow id; a workflow without an entry has no tasks yet. */
  tasks: Record<string, Task[]>
  runs: WorkflowRun[]
  /** Log lines per task run id. */
  logs: Record<number, LogLine[]>
  datasets: Dataset[]
}

/** Requests the mock received, for assertions. */
export interface MockRecorder {
  createdRuns: WorkflowRunCreate[]
  data: MockData
}

const json = (body: unknown, status = 200) => ({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

export function workflow(overrides: Partial<Workflow> & { title: string }): Workflow {
  return {
    id: `${overrides.title}-${overrides.increment ?? 1}`,
    increment: 1,
    workflow_engine: 'airflow',
    created_at: '2026-09-01T10:00:00Z',
    definition: '',
    labels: [],
    workflow_parameters: [],
    ...overrides,
  }
}

export function task(id: number, title: string, workflowId: string): Task {
  return { id, title, workflow_revision_id: workflowId, downstream_task_ids: [] }
}

export function taskRun(
  id: number,
  runId: number,
  title: string,
  status = TaskRunStatus.COMPLETED,
): TaskRun {
  return {
    id,
    task_id: id,
    workflow_run_id: runId,
    task_title: title,
    lifecycle_status: status,
    external_id: null,
  }
}

export function run(overrides: Partial<WorkflowRun> & { id: number }): WorkflowRun {
  return {
    workflow: { id: 'segmentation-2', title: 'Segmentation', increment: 2 },
    labels: [],
    external_id: `ext-${overrides.id}`,
    created_at: '2026-10-01T08:00:00Z',
    updated_at: '2026-10-01T08:30:00Z',
    lifecycle_status: WorkflowRunStatus.COMPLETED,
    task_runs: [],
    cleanup_policy: 'never',
    cleanup_status: 'not_required',
    ...overrides,
  }
}

export function logLine(
  message: string,
  severity = 'INFO',
  time = '2026-10-01T08:00:01Z',
): LogLine {
  return { time, severity, message, metadata: {} }
}

const segmentationParameters: WorkflowParameter[] = [
  {
    task_title: 'segment',
    env_variable_name: 'DATASET',
    ui_form: { type: 'dataset', title: 'Dataset', description: 'Input data.', required: true },
  },
  {
    task_title: 'segment',
    env_variable_name: 'THRESHOLD',
    ui_form: {
      type: 'int',
      title: 'Threshold',
      description: 'Segmentation threshold.',
      minimum: 1,
      maximum: 10,
      default: 5,
      required: true,
      help: 'Higher values keep fewer voxels.',
    },
  },
  {
    task_title: 'export',
    env_variable_name: 'FORMAT',
    ui_form: {
      type: 'list',
      title: 'Format',
      description: 'Export format.',
      options: ['nifti', 'dicom'],
    },
  },
]

export function defaultMockData(): MockData {
  const segmentationV1 = workflow({
    title: 'Segmentation',
    id: 'segmentation-1',
    increment: 1,
    labels: [{ key: 'kaapana-ui.category', value: 'Segmentation' }],
    workflow_parameters: segmentationParameters,
  })
  const segmentationV2 = workflow({
    title: 'Segmentation',
    id: 'segmentation-2',
    increment: 2,
    labels: [
      { key: 'kaapana-ui.category', value: 'Segmentation' },
      { key: 'kaapana-ui.provider', value: 'DKFZ' },
      { key: 'kaapana-ui.maturity', value: 'stable' },
      { key: 'kaapana-ui.description', value: 'Segments organs in CT images.' },
    ],
    workflow_parameters: segmentationParameters,
  })
  const registration = workflow({
    title: 'Registration',
    id: 'registration-1',
    labels: [
      { key: 'kaapana-ui.category', value: 'Registration' },
      { key: 'kaapana-ui.provider', value: 'Partner' },
      { key: 'kaapana-ui.maturity', value: 'experimental' },
    ],
  })
  const parsing = workflow({ title: 'Anonymization', id: 'anonymization-1' })

  return {
    workflows: [segmentationV1, segmentationV2, registration, parsing],
    tasks: {
      'segmentation-1': [task(1, 'segment', 'segmentation-1'), task(2, 'export', 'segmentation-1')],
      'segmentation-2': [task(3, 'segment', 'segmentation-2'), task(4, 'export', 'segmentation-2')],
      'registration-1': [task(5, 'register', 'registration-1')],
    },
    runs: [
      run({
        id: 1,
        lifecycle_status: WorkflowRunStatus.COMPLETED,
        created_at: '2026-09-28T09:00:00Z',
        cleanup_policy: 'on_success',
        // The started run stores the chosen values in each ui_form.default.
        workflow_parameters: [
          {
            ...segmentationParameters[0],
            ui_form: { ...segmentationParameters[0].ui_form, default: 'lung-ct' },
          },
          {
            ...segmentationParameters[1],
            ui_form: { ...segmentationParameters[1].ui_form, default: 7 },
          },
          {
            ...segmentationParameters[2],
            ui_form: { ...segmentationParameters[2].ui_form, default: null },
          },
        ],
        task_runs: [taskRun(11, 1, 'segment'), taskRun(12, 1, 'export')],
      }),
      run({
        id: 2,
        lifecycle_status: WorkflowRunStatus.RUNNING,
        created_at: '2026-10-01T09:00:00Z',
        task_runs: [taskRun(21, 2, 'segment', TaskRunStatus.RUNNING)],
      }),
      run({
        id: 3,
        workflow: { id: 'registration-1', title: 'Registration', increment: 1 },
        lifecycle_status: WorkflowRunStatus.ERROR,
        created_at: '2026-09-30T09:00:00Z',
        task_runs: [taskRun(31, 3, 'register', TaskRunStatus.ERROR)],
      }),
    ],
    logs: {
      11: [
        logLine('Loading dataset lung-ct'),
        logLine('Low contrast in slice 12', 'WARNING'),
        logLine('Done'),
      ],
      12: [logLine('Exporting to nifti'), logLine('Export finished')],
      21: [logLine('Segmenting slice 1')],
      31: [logLine('Starting registration'), logLine('Fixed image is missing', 'ERROR')],
    },
    datasets: [
      { name: 'lung-ct', time_created: '', time_updated: '', username: 'admin', identifiers: [] },
      { name: 'brain-mri', time_created: '', time_updated: '', username: 'admin', identifiers: [] },
    ],
  }
}

export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
  })
}

const ACTIVE = [
  WorkflowRunStatus.CREATED,
  WorkflowRunStatus.PENDING,
  WorkflowRunStatus.SCHEDULED,
  WorkflowRunStatus.RUNNING,
]
const FINISHED = [WorkflowRunStatus.COMPLETED, WorkflowRunStatus.ERROR, WorkflowRunStatus.CANCELED]

const CLEANUP_IN_PROGRESS = ['pending', 'running']

const conflict = (detail: string) => json({ detail }, 409)

function runIdOf(route: Route) {
  return Number(new URL(route.request().url()).pathname.match(/workflow-runs\/(\d+)/)?.[1])
}

/**
 * Intercept every backend call of the view so it boots without a platform.
 * Mutating actions update `data`, so a reload shows their effect. Later
 * page.route calls override these.
 */
export async function installMockBackend(
  page: Page,
  data: MockData = defaultMockData(),
): Promise<MockRecorder> {
  const recorder: MockRecorder = { createdRuns: [], data }
  await seedShellState(page)

  await page.route('**/workflow-api/v1/workflows', (r) => r.fulfill(json(data.workflows)))
  await page.route(/\/workflow-api\/v1\/workflows\/[^/]+\/tasks$/, (r) => {
    const id = decodeURIComponent(new URL(r.request().url()).pathname.split('/').at(-2)!)
    return r.fulfill(json(data.tasks[id] ?? []))
  })

  await page.route('**/workflow-api/v1/workflow-runs', (r) => {
    if (r.request().method() !== 'POST') return r.fulfill(json(data.runs))
    const body = r.request().postDataJSON() as WorkflowRunCreate
    recorder.createdRuns.push(body)
    const created = run({
      id: Math.max(0, ...data.runs.map((x) => x.id)) + 1,
      workflow: body.workflow,
      lifecycle_status: WorkflowRunStatus.CREATED,
    })
    data.runs = [...data.runs, created]
    return r.fulfill(json(created))
  })

  await page.route(/\/workflow-api\/v1\/workflow-runs\/\d+$/, (r) => {
    const found = data.runs.find((x) => x.id === runIdOf(r))
    if (!found) return r.fulfill(json({ detail: 'Workflow run not found' }, 404))
    if (r.request().method() !== 'DELETE') return r.fulfill(json(found))
    if (!FINISHED.includes(found.lifecycle_status)) {
      return r.fulfill(
        conflict(`Run ${found.id} is ${found.lifecycle_status} and cannot be deleted.`),
      )
    }
    if (CLEANUP_IN_PROGRESS.includes(found.cleanup_status ?? 'not_required')) {
      return r.fulfill(conflict(`The data of run ${found.id} is being cleaned. Try again later.`))
    }
    data.runs = data.runs.filter((x) => x.id !== found.id)
    return r.fulfill({ status: 204 })
  })

  const transition = (status: WorkflowRunStatus) => (r: Route) => {
    const id = runIdOf(r)
    data.runs = data.runs.map((x) => (x.id === id ? { ...x, lifecycle_status: status } : x))
    return r.fulfill(json(data.runs.find((x) => x.id === id)))
  }
  await page.route(/\/workflow-runs\/\d+\/cancel$/, (r) => {
    const found = data.runs.find((x) => x.id === runIdOf(r))!
    if (!ACTIVE.includes(found.lifecycle_status)) {
      return r.fulfill(
        conflict(`Run ${found.id} is ${found.lifecycle_status} and cannot be canceled.`),
      )
    }
    return transition(WorkflowRunStatus.CANCELED)(r)
  })
  await page.route(/\/workflow-runs\/\d+\/retry$/, (r) => {
    const found = data.runs.find((x) => x.id === runIdOf(r))!
    if (![WorkflowRunStatus.ERROR, WorkflowRunStatus.CANCELED].includes(found.lifecycle_status)) {
      return r.fulfill(
        conflict(`Run ${found.id} is ${found.lifecycle_status} and cannot be retried.`),
      )
    }
    if (!found.external_id) {
      return r.fulfill(
        conflict(`Run ${found.id} never reached the engine, so it cannot be retried.`),
      )
    }
    if (CLEANUP_IN_PROGRESS.includes(found.cleanup_status ?? 'not_required')) {
      return r.fulfill(
        conflict(`The data of run ${found.id} is being cleaned, so it cannot be retried.`),
      )
    }
    if (found.cleanup_status === 'cleaned') {
      return r.fulfill(
        conflict(`The data of run ${found.id} was cleaned, so it cannot be retried.`),
      )
    }
    return transition(WorkflowRunStatus.PENDING)(r)
  })
  await page.route(/\/workflow-runs\/\d+\/clean$/, (r) => {
    const id = runIdOf(r)
    data.runs = data.runs.map((x) => (x.id === id ? { ...x, cleanup_status: 'pending' } : x))
    return r.fulfill(json(data.runs.find((x) => x.id === id)))
  })

  await page.route(/\/workflow-runs\/\d+\/task-runs\/\d+\/logs$/, (r) => {
    const taskId = Number(new URL(r.request().url()).pathname.split('/').at(-2))
    return r.fulfill(json(data.logs[taskId] ?? []))
  })

  await page.route('**/kaapana-backend/client/datasets*', (r) => r.fulfill(json(data.datasets)))

  return recorder
}
