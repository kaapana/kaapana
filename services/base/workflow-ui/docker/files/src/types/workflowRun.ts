import type { Label } from "./label"
import type { TaskRun } from "./taskRun"
import type { WorkflowRunStatus } from "./enum"
import { ConfigDefinition } from "./workflow"

export interface WorkflowRef {
  title: string
  version: number
}

export interface WorkflowRunBase {
  workflow: WorkflowRef
  labels: Label[]
  config?: ConfigDefinition
}

export interface WorkflowRunCreate extends WorkflowRunBase {}

export interface WorkflowRun extends WorkflowRunBase {
  id: number
  external_id?: string
  created_at: string
  lifecycle_status: WorkflowRunStatus
  task_runs: TaskRun[]
  updated_at: string
}

export interface WorkflowRunUpdate {
  external_id?: string
  lifecycle_status?: WorkflowRunStatus
}
