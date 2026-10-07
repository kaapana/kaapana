import { httpClient } from '@kaapana/base-ui'
import type { LogLine, WorkflowRun, WorkflowRunCreate } from '@/types/schemas'

const API_BASE = '/workflow-api/v1/workflow-runs'

export const workflowRunsApi = {
  async create(workflowRunCreate: WorkflowRunCreate): Promise<WorkflowRun> {
    const response = await httpClient.post<WorkflowRun>(API_BASE, workflowRunCreate)
    return response.data
  },

  async getAll(): Promise<WorkflowRun[]> {
    const response = await httpClient.get<WorkflowRun[]>(API_BASE)
    return Array.isArray(response.data) ? response.data : []
  },

  async getById(workflowRunId: number): Promise<WorkflowRun> {
    const response = await httpClient.get<WorkflowRun>(`${API_BASE}/${workflowRunId}`)
    return response.data
  },

  async cancel(workflowRunId: number): Promise<WorkflowRun> {
    const response = await httpClient.put<WorkflowRun>(`${API_BASE}/${workflowRunId}/cancel`)
    return response.data
  },

  async retry(workflowRunId: number): Promise<WorkflowRun> {
    const response = await httpClient.put<WorkflowRun>(`${API_BASE}/${workflowRunId}/retry`)
    return response.data
  },

  async clean(workflowRunId: number): Promise<WorkflowRun> {
    const response = await httpClient.post<WorkflowRun>(`${API_BASE}/${workflowRunId}/clean`)
    return response.data
  },

  async delete(workflowRunId: number): Promise<void> {
    await httpClient.delete(`${API_BASE}/${workflowRunId}`)
  },

  async getTaskRunLogLines(workflowRunId: number, taskRunId: number): Promise<LogLine[]> {
    const response = await httpClient.get<LogLine[]>(
      `${API_BASE}/${workflowRunId}/task-runs/${taskRunId}/logs`,
    )
    return Array.isArray(response.data) ? response.data : []
  },
}
