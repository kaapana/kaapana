import type { Label } from "./label"

export interface WorkflowParameterUI {
  type: 'string' | 'text' | 'number' | 'integer' | 'boolean' | 'select' | 'multiselect' | 'textarea' | 'date' | 'datetime' | 'file'
  options?: string[]
  default?: any
  minimum?: number
  maximum?: number
}

export interface DataSelectionUI {
  query?: string
  kaapana_backend_identifiers: string[]
  kaapana_backend_dataset_name?: string
}

export interface WorkflowParameter {
  title: string
  description?: string
  env_variable_name: string
  required?: boolean
  ui_params: WorkflowParameterUI | DataSelectionUI
  category?: string
}

export interface ConfigDefinition {
  // map of task-title -> list of WorkflowParameter
  workflow_parameters?: Record<string, WorkflowParameter[]>
}
export interface WorkflowBase {
  title: string
  definition: string
  workflow_engine: string

  config_definition?: ConfigDefinition
  labels: Label[]
}

export interface WorkflowCreate extends WorkflowBase { }

export interface Workflow extends WorkflowBase {
  id: number
  version: number
  created_at: string // ISO date string from backend
}
