import type { TaskRunStatus } from "./enum"

export interface TaskRunBase {
  task_title: string
  lifecycle_status: TaskRunStatus
  external_id: string
}

export interface TaskRunCreate extends TaskRunBase {
  workflow_run_id: number
  task_id: number
}

export interface TaskRun extends TaskRunBase {
  id: number
  task_id: number
  workflow_run_id: number
}

export interface TaskRunUpdate {
  external_id?: string
  lifecycle_status?: TaskRunStatus
}