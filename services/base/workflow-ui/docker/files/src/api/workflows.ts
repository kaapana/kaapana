import { httpClient } from '@kaapana/base-ui'
import { WORKFLOW_API_URL } from '@/api/config'
import type { Task, Workflow } from '@/types/schemas'

const API_BASE = `${WORKFLOW_API_URL}/workflows`

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
