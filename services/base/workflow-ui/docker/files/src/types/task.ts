export interface TaskBase {
  display_name?: string
  title: string
  type?: string
}

export interface TaskCreate extends TaskBase {
  downstream_task_titles: string[]
}

export interface Task extends TaskBase {
  id: number
  workflow_id: number
  downstream_task_ids: number[]
}