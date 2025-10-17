import type { Label } from "./label"

// Based on backend WorkflowParameterUI and DataSelectionUI
export interface WorkflowParameterUI {
  type: 'string' | 'text' | 'number' | 'integer' | 'boolean' | 'select' | 'multiselect' | 'textarea' | 'date' | 'datetime' | 'file'
  options?: string[]
  default?: any
  minimum?: number
  maximum?: number
  step?: number
  rows?: number
  placeholder?: string
  group?: string
}

export interface DataSelectionUI {
  query?: string
  kaapana_backend_identifiers: string[]
  kaapana_backend_dataset_name?: string
}

export interface WorkflowParameter {
  title: string
  description?: string
  task_title: string
  env_variable_name: string
  required?: boolean
  ui_params: WorkflowParameterUI | DataSelectionUI
  category?: string
}

export interface WorkflowBase {
  title: string
  definition: string
  workflow_engine: string
  // New shape: map of task-title -> list of WorkflowParameter
  // This replaces the old ConfigDefinition.workflow_parameters
  parameters?: Record<string, WorkflowParameter[]>
  // Keep labels
  labels: Label[]
}

export interface WorkflowCreate extends WorkflowBase { }

export interface Workflow extends WorkflowBase {
  id: number
  version: number
  created_at: string // ISO date string from backend
}
