import apiClient from './apiClient'
import { toRaw } from 'vue'
import type { WorkflowRun, WorkflowRunCreate, WorkflowRunUpdate } from '@/types/workflowRun'

const API_BASE = '/workflow-runs'

function safeSerializeToObject(obj: unknown, maxDepth = 40): unknown {
  // Unwrap Vue reactive proxies first
  const root = typeof obj === 'object' && obj !== null ? (toRaw(obj as Record<string, unknown>) ?? obj) : obj

  const seen = new WeakMap<object, unknown>()

  function clone(value: unknown, depth: number): unknown {
    if (value === null || typeof value !== 'object') return value
    if (depth > maxDepth) return undefined
    const vObj = value as object
    if (seen.has(vObj)) return undefined
    seen.set(vObj, true)

    if (Array.isArray(value)) {
      return (value as unknown[]).map((item) => clone(item, depth + 1))
    }

    if (value instanceof Date) return value.toISOString()
    if (value instanceof Map) return Array.from((value as Map<unknown, unknown>).entries()).map(([k, v]) => [k, clone(v, depth + 1)])
    if (value instanceof Set) return Array.from(value as Set<unknown>).map((v) => clone(v, depth + 1))

    const out: Record<string, unknown> = {}
    // only copy own enumerable keys
    for (const key of Object.keys(value as Record<string, unknown>)) {
      try {
        out[key] = clone((value as Record<string, unknown>)[key], depth + 1)
      } catch {
        out[key] = undefined
      }
    }
    return out
  }

  return clone(root, 0)
}

function getErrorDetail(err: unknown): string | undefined {
  if (typeof err === 'object' && err !== null) {
    const e = err as { response?: { data?: { detail?: string } }; message?: string }
    return e.response?.data?.detail ?? e.message
  }
  return undefined
}

export const workflowRunsApi = {
  async create(workflowRunCreate: WorkflowRunCreate): Promise<WorkflowRun> {
    try {
      const clean = safeSerializeToObject(workflowRunCreate)
      const response = await apiClient.post<WorkflowRun>(API_BASE, clean)
      return response.data
    } catch (err: unknown) {
      const detail = getErrorDetail(err)
      throw new Error(detail || 'Failed to create workflow run')
    }
  },

  async getAll(params?: { workflow_title?: string; workflow_version?: number }): Promise<WorkflowRun[]> {
    const response = await apiClient.get<WorkflowRun[]>(API_BASE, { params })
    return response.data
  },

  async getById(workflowRunId: number): Promise<WorkflowRun> {
    const response = await apiClient.get<WorkflowRun>(`${API_BASE}/${workflowRunId}`)
    return response.data
  },

  async update(workflowRunId: number, payload: WorkflowRunUpdate): Promise<WorkflowRun> {
    const clean = safeSerializeToObject(payload)
    const response = await apiClient.patch<WorkflowRun>(`${API_BASE}/${workflowRunId}`, clean)
    return response.data
  },

  async delete(workflowRunId: number): Promise<void> {
    await apiClient.delete(`${API_BASE}/${workflowRunId}`)
  },

  async cancel(workflowRunId: number): Promise<WorkflowRun> {
    const response = await apiClient.put<WorkflowRun>(`${API_BASE}/${workflowRunId}/cancel`)
    return response.data
  },

  async retry(workflowRunId: number): Promise<WorkflowRun> {
    const response = await apiClient.put<WorkflowRun>(`${API_BASE}/${workflowRunId}/retry`)
    return response.data
  },
}
