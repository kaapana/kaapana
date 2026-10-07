export interface Label {
  key: string
  value: string
}

export interface Dataset {
  name: string
  time_created: string
  time_updated: string
  username: string
  identifiers: string[]
}

export enum WorkflowRunStatus {
  CREATED = 'Created',
  PENDING = 'Pending',
  SCHEDULED = 'Scheduled',
  RUNNING = 'Running',
  ERROR = 'Error',
  COMPLETED = 'Completed',
  CANCELED = 'Canceled',
}

export enum TaskRunStatus {
  CREATED = 'Created',
  PENDING = 'Pending',
  SCHEDULED = 'Scheduled',
  RUNNING = 'Running',
  ERROR = 'Error',
  COMPLETED = 'Completed',
  SKIPPED = 'Skipped',
  UPSTREAM_FAILED = 'Upstream Failed',
}

export type CleanupPolicy = 'never' | 'on_success' | 'always'
export type CleanupStatus = 'not_required' | 'pending' | 'running' | 'cleaned' | 'failed'

// ##########################
// #### UI Forms #############
// ##########################
export type BaseUIForm = {
  type: string
  title: string
  description: string
  help?: string
  required?: boolean
  default?: any
}

export interface BooleanUIForm extends BaseUIForm {
  type: 'bool'
  true_label?: string
  false_label?: string
}

export interface IntegerUIForm extends BaseUIForm {
  type: 'int'
  minimum?: number
  maximum?: number
}

export interface FloatUIForm extends BaseUIForm {
  type: 'float'
  minimum?: number
  maximum?: number
}

export interface ListUIForm extends BaseUIForm {
  type: 'list'
  options?: string[]
  multiselectable?: boolean
}

export interface StringUIForm extends BaseUIForm {
  type: 'str'
  regex_pattern: string
}

export interface DatasetUIForm extends BaseUIForm {
  type: 'dataset'
}

export interface DataEntitiesUIForm extends BaseUIForm {
  type: 'data_entity'
  query: string
  limit: number
  pagination: boolean
}

export interface TermsUIForm extends BaseUIForm {
  type: 'terms'
  terms_text: string
}

// Union for discriminated UIForm
export type UIForm =
  | BooleanUIForm
  | IntegerUIForm
  | FloatUIForm
  | ListUIForm
  | StringUIForm
  | DatasetUIForm
  | DataEntitiesUIForm
  | TermsUIForm

// ##########################
// #### WorkflowParameter ###
// ##########################
export interface WorkflowParameter {
  task_title: string
  env_variable_name: string
  ui_form: UIForm
}

// ##########################
// ########## Task ##########
// ##########################
export interface TaskBase {
  display_name?: string
  title: string
  type?: string
}

export interface Task extends TaskBase {
  id: number
  workflow_revision_id: string
  downstream_task_ids: number[]
}

// ##########################
// ######## Task Run ########
// ##########################

export interface TaskRunBase {
  task_title: string
  lifecycle_status: TaskRunStatus
  external_id: string | null
}

export interface TaskRun extends TaskRunBase {
  id: number
  task_id: number
  workflow_run_id: number
}

// ##########################
// ######## Workflow ########
// ##########################

// Versioned content of a workflow
export interface MutableWorkflowBase {
  definition: string
  workflow_parameters?: WorkflowParameter[]
  labels: Label[]
}

// Workflow object with stable identity + the latest revision's content merged in.
export interface Workflow extends MutableWorkflowBase {
  id: string
  title: string
  workflow_engine: string
  created_at: string
  increment: number
}

// ##########################
// ###### Workflow Run ######
// ##########################
export interface WorkflowRef {
  id: string
  // Filled by server on responses; not required on POST /workflow-runs.
  title?: string
  increment: number
}

export interface WorkflowRunBase {
  workflow: WorkflowRef
  labels: Label[]
  workflow_parameters?: WorkflowParameter[]
}

export interface WorkflowRunCreate extends WorkflowRunBase {
  cleanup_policy?: CleanupPolicy
}

export interface WorkflowRun extends WorkflowRunBase {
  id: number
  external_id?: string | null
  created_at: string
  lifecycle_status: WorkflowRunStatus
  task_runs: TaskRun[]
  updated_at: string
  cleanup_policy: CleanupPolicy
  cleanup_status: CleanupStatus
  cleaned_at?: string | null
}

// ##########################
// ######## Log Line ########
// ##########################
export interface LogLine {
  time: string
  severity: string
  message: string
  metadata: Record<string, string>
}
