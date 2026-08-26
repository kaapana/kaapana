import type { Page } from '@playwright/test'

export const UNSCOPED_VIEW_PATH = '/workflow-execution-ui/'
// The /project/<short_id> document prefix IS the project selection
// (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/workflow-execution-ui/'

// The view's API layer (@kaapana/base-ui) is untyped, so the wire contracts are
// defined locally; type-check cannot catch drift against the backend.

export interface KaapanaInstance {
  instance_name: string
  remote: boolean
  allowed_dags: string[]
}

// vjsf-2-dialect JSON schema (workflow_form / data_form / ...); the backend
// emits the v2 dialect and the component runs it through v2compat.
export type FormSchema = Record<string, any>

// schemas_dict: dag_id -> { form_name -> schema }
export type SchemasDict = Record<string, Record<string, FormSchema>>

export interface Userinfo {
  preferredUsername: string
  groups: string[]
  user: string
}

// The shell-owned localStorage["settings"] blob. Only `darkMode` (App.vue) and
// `workflows` (WorkflowExecution.loadWorkflowSettings) are read by this view.
export interface ShellSettings {
  darkMode?: boolean
  workflows?: Record<string, { properties: Record<string, any>; hideOnUI: string[] }>
  [k: string]: unknown
}

export interface ShellProject {
  id: number
  name: string
  short_id: string
}

export interface MockData {
  userinfo: Userinfo
  instances: KaapanaInstance[]
  dags: string[]
  schemas: SchemasDict
}

// ---- Mock DAG schemas: modelled on real Kaapana ui_forms; each dag isolates
// one concern so specs stay focused. ----------------------------------------

const allFieldsSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      text_field: {
        type: 'string',
        title: 'Text Field',
        default: 'hello',
        description: 'The text to process',
      },
      algorithm: {
        type: 'string',
        title: 'Algorithm',
        enum: ['alpha', 'beta', 'gamma'],
        default: 'alpha',
      },
      enabled: { type: 'boolean', title: 'Enabled', default: false },
      threshold: { type: 'integer', title: 'Threshold', default: 5 },
      ratio: { type: 'number', title: 'Ratio', default: 0.5 },
      tags: {
        type: 'array',
        title: 'Tags',
        items: { type: 'string', title: 'Tag' },
        default: [],
      },
      advanced: {
        type: 'object',
        title: 'Advanced',
        properties: {
          retries: { type: 'integer', title: 'Retries', default: 3 },
        },
      },
    },
  },
}

// Settings-mechanism fixture: the settings lookup key is camelCase(dag_id) =>
// `settingsDemo` (see defaultSettings.workflows). No property-level `required`
// here — that would blank the form (see validateDicomsRealSchema).
const settingsDemoSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      validator_algorithm: {
        title: 'Validator Algorithm',
        enum: ['dicom-validator', 'dciodvfy'],
        type: 'string',
        default: 'dicom-validator',
      },
      exit_on_error: {
        title: 'Stop execution on Validation Error',
        type: 'boolean',
        default: false,
      },
      tags_whitelist: {
        type: 'array',
        title: 'Tags Whitelist',
        items: { type: 'string', title: 'DICOM tag' },
        default: [],
      },
    },
  },
}

// The real validate-dicoms ui_form verbatim: property-level `required: true` is
// a boolean, which raw vjsf 3 rejects ("required must be array"); the component
// must normalize it into a parent-level `required` array.
const validateDicomsRealSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      validator_algorithm: {
        title: 'Validator Algorithm',
        enum: ['dicom-validator', 'dciodvfy'],
        type: 'string',
        default: 'dicom-validator',
        required: true,
      },
      exit_on_error: { title: 'Stop execution on Validation Error', type: 'boolean', default: false },
    },
  },
}

// Required string with no default: submit must stay blocked until filled.
const requiredFieldSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      aetitle: { type: 'string', title: 'AE Title', required: true },
    },
  },
}

// validConfirmation(): a boolean property literally named `confirmation` must
// be true before submit.
const confirmationSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      note: { type: 'string', title: 'Note', default: 'ok' },
      confirmation: { type: 'boolean', title: 'I accept the terms', default: false },
    },
  },
}

// data_form with the dataset_name oneOf select the backend injects per project.
const datasetSchema: Record<string, FormSchema> = {
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
}

// Conditional field via draft-07 `dependencies` + oneOf, the pattern real DAGs
// (classification/nnunet) use: `extra_param` only appears when mode==='advanced'.
const conditionalSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      mode: { type: 'string', title: 'Mode', enum: ['simple', 'advanced'], default: 'simple' },
    },
    dependencies: {
      mode: {
        oneOf: [
          { properties: { mode: { const: 'simple' } } },
          {
            properties: {
              mode: { const: 'advanced' },
              extra_param: { type: 'string', title: 'Extra Param' },
            },
          },
        ],
      },
    },
  },
}

// documentation_form renders as a doc link, not a vjsf form.
const documentedSchema: Record<string, FormSchema> = {
  documentation_form: { path: '/user_guide/system/airflow.html#send-dicom' },
  workflow_form: {
    type: 'object',
    properties: {
      pacs_port: { title: 'Receiver port', type: 'integer', default: 11112 },
    },
  },
}

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  instances: [{ instance_name: 'local-instance', remote: false, allowed_dags: [] }],
  dags: [
    'mock-all-fields',
    'settings-demo',
    'mock-confirmation',
    'mock-dataset',
    'mock-conditional',
    'mock-documented',
    'validate-dicoms',
    'mock-required',
  ],
  schemas: {
    'mock-all-fields': allFieldsSchema,
    'settings-demo': settingsDemoSchema,
    'mock-confirmation': confirmationSchema,
    'mock-dataset': datasetSchema,
    'mock-conditional': conditionalSchema,
    'mock-documented': documentedSchema,
    'validate-dicoms': validateDicomsRealSchema,
    'mock-required': requiredFieldSchema,
  },
}

// Shell-seeded settings, shaped like portal-ui's defaultUIConfig.ts (dag name camelCased).
// Every workflows entry MUST include a hideOnUI array — the app's
// `wfOptions.hideOnUI.includes(...)` is unguarded.
export const defaultSettings: ShellSettings = {
  darkMode: false,
  workflows: {
    settingsDemo: {
      properties: {
        validator_algorithm: 'dciodvfy',
        exit_on_error: false,
        tags_whitelist: [],
      },
      hideOnUI: ['tags_whitelist'],
    },
  },
}

// The view never fetches a project list — the /project/<short_id> document
// prefix is its only project input — so these exist purely to build scoped URLs.
export const shellProjects: ShellProject[] = [
  { id: 1, name: 'admin', short_id: 'admin' },
  { id: 2, name: 'research-b', short_id: 'resb' },
]

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: ShellProject): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

/**
 * Intercept every backend call the view makes so it runs without a platform.
 * Call before page.goto(); add per-test page.route() overrides *after* this
 * call (later routes win in Playwright).
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  // Auth: prod build asks the oauth2 proxy, dev server a static token file.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))

  await page.route('**/kaapana-backend/client/get-kaapana-instances', (r) =>
    r.fulfill(json(data.instances)),
  )
  await page.route('**/kaapana-backend/client/get-dags', (r) => r.fulfill(json(data.dags)))
  await page.route('**/kaapana-backend/client/get-ui-form-schemas', (r) =>
    r.fulfill(json(data.schemas)),
  )
  await page.route('**/kaapana-backend/client/workflow', (r) => r.fulfill(json({ workflow_id: 'wf-1' })))

  // Federated header lookup; only hit on the remote-runner branch.
  await page.route('**/kaapana-backend/client/kaapana-instance', (r) =>
    r.fulfill(json({ token: 'mock-token' })),
  )

  // On successful submit navigateShell (with no shell around) navigates
  // window.top to the literal shell route '/web/workflows/workflows'; stub it
  // so the navigation doesn't hit a dead URL.
  await page.route('**/workflows/workflows', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><html><body>stub</body></html>' }),
  )
}

/**
 * Seed the shell-owned localStorage["settings"] before the view boots. The
 * project is NOT seeded — it travels in the document URL (/project/<short_id>/).
 */
export async function seedShellState(page: Page, settings: ShellSettings = defaultSettings) {
  await page.addInitScript((s) => {
    localStorage.setItem('settings', s)
  }, JSON.stringify(settings))
}

/** Seed shell storage, install the mock backend, navigate, wait for boot. */
export async function bootView(
  page: Page,
  data: MockData = defaultMockData,
  settings: ShellSettings = defaultSettings,
) {
  await seedShellState(page, settings)
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)
  // The dag field only renders once the instance -> dags/schemas chain resolved.
  await workflowField(page).waitFor({ state: 'visible' })
}

/** The single-select "Workflow" dag field (a combobox, distinct from the
 *  "Workflow name" textbox and the runner-instances multi-select). */
export function workflowField(page: Page) {
  return page.getByRole('combobox', { name: 'Workflow', exact: true })
}

export async function selectDag(page: Page, dagId: string) {
  await workflowField(page).click()
  await page.getByRole('option', { name: dagId, exact: true }).click()
  // Let the dag_id watcher rebuild schemas and vjsf re-render.
  await page.locator('.v-overlay--active').waitFor({ state: 'hidden' }).catch(() => {})
}

// ---- Realistic DAG shapes that crashed vjsf 3 on the live platform ----------
// Reproduced from actual /client/get-ui-form-schemas output; each blanked the
// whole execution form. The fixtures pin the fixes (see realistic-dags.spec.ts).

export function singleDagData(dag: string, schema: Record<string, FormSchema>): MockData {
  return { ...defaultMockData, dags: [dag], schemas: { [dag]: schema } }
}

// On a busy project the dataset_name oneOf holds thousands of branches; vjsf 3
// builds one node per branch and ~1000+ overflows the render call stack.
// Generated so the size that triggers the crash is exercised for real.
export function largeDatasetSchema(n = 1500): Record<string, FormSchema> {
  const oneOf = Array.from({ length: n }, (_, i) => ({
    const: { name: `ds-${i}`, username: 'kaapana', access_level: 'project' },
    title: `ds-${i} (project) (${i})`,
  }))
  return {
    workflow_form: {
      type: 'object',
      properties: {
        single_execution: { type: 'boolean', title: 'Single execution', default: false },
      },
    },
    data_form: {
      type: 'object',
      properties: {
        dataset_name: { type: 'string', title: 'Dataset name (size)', required: true, oneOf },
        dataset_limit: { type: 'integer', title: 'Limit dataset size' },
      },
    },
  }
}

// nnunet-predict with no model installed: the backend emits tasks as a required
// string with an EMPTY oneOf, which raw vjsf 3 rejects and crashes the form;
// normalizeV2Schema must strip it so the informational title still shows.
export const noModelsSchema: Record<string, FormSchema> = {
  workflow_form: {
    type: 'object',
    properties: {
      tasks: {
        title: 'No tasks are available in this project!',
        description: 'You first have to install a task with nnunet-install-model.',
        oneOf: [],
        type: 'string',
        readOnly: false,
        required: true,
      },
    },
  },
  data_form: {
    type: 'object',
    properties: {
      dataset_name: {
        type: 'string',
        title: 'Dataset name (size)',
        required: true,
        oneOf: [
          { const: { name: 'nsclc', username: 'kaapana', access_level: 'project' }, title: 'nsclc (project) (42)' },
        ],
      },
    },
  },
}

// import-*-from-data-upload before anything is uploaded: items.enum is EMPTY,
// ajv rejects `enum: []` and the whole form fails to compile; normalizeV2Schema
// must strip it.
export const emptyUploadSchema: Record<string, FormSchema> = {
  data_form: {
    type: 'object',
    properties: {
      action_files: {
        title: 'Objects from uploads directory',
        description: 'Relative paths to object in upload directory',
        type: 'array',
        items: { type: 'string', enum: [] },
        readOnly: false,
      },
    },
  },
}
