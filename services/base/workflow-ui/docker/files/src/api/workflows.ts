import { httpClient } from '@kaapana/base-ui'
import type { Task, Workflow } from '@/types/schemas'

const API_BASE = '/workflow-api/v1/workflows'

export async function fetchWorkflows(): Promise<Workflow[]> {
  const response = await httpClient.get<Workflow[]>(API_BASE)
  return Array.isArray(response.data) ? response.data : []
}

// Tasks of the workflow revision with the given id. They exist once the
// workflow engine has parsed the definition.
export async function fetchWorkflowTasks(workflowId: string): Promise<Task[]> {
  const response = await httpClient.get<Task[]>(`${API_BASE}/${workflowId}/tasks`)
  return Array.isArray(response.data) ? response.data : []
}
