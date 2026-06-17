import apiClient from './workflowApiClient';
import type {
    Workflow,
    WorkflowCreate,
    WorkflowRevision,
    WorkflowUpdate,
} from '@/types/schemas';


// Fetch all workflows
export async function fetchWorkflows(params?: { title?: string }): Promise<Workflow[]> {
    const response = await apiClient.get<Workflow[]>('/workflows', { params });
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}

// Fetch a single workflow by UUID
export async function fetchWorkflowById(id: string): Promise<Workflow> {
    const response = await apiClient.get<Workflow>(`/workflows/${id}`);
    return response.data;
}

// Create a new workflow
export async function createWorkflow(workflow: WorkflowCreate): Promise<Workflow> {
    const response = await apiClient.post<Workflow>('/workflows', workflow);
    return response.data;
}

// Patch a workflow (creates a new revision)
export async function patchWorkflow(id: string, update: WorkflowUpdate): Promise<Workflow> {
    const response = await apiClient.patch<Workflow>(`/workflows/${id}`, update);
    return response.data;
}

// Delete a workflow (soft-delete)
export async function deleteWorkflow(id: string): Promise<void> {
    await apiClient.delete(`/workflows/${id}`);
}

// Fetch tasks for a workflow by UUID (current revision)
export async function fetchWorkflowTasks(workflowId: string) {
    const response = await apiClient.get(`/workflows/${workflowId}/tasks`)
    return response.data
}

// List all revisions of a workflow
export async function fetchWorkflowRevisions(workflowId: string): Promise<WorkflowRevision[]> {
    const response = await apiClient.get<WorkflowRevision[]>(`/workflows/${workflowId}/revisions`);
    return response.data;
}

// Fetch a specific revision by increment
export async function fetchWorkflowRevision(
    workflowId: string,
    increment: number,
): Promise<WorkflowRevision> {
    const response = await apiClient.get<WorkflowRevision>(
        `/workflows/${workflowId}/revisions/${increment}`,
    );
    return response.data;
}

// Restore (rewind) a workflow to a specific revision; creates a new increment with that content.
export async function restoreWorkflowRevision(
    workflowId: string,
    increment: number,
): Promise<Workflow> {
    const response = await apiClient.post<Workflow>(
        `/workflows/${workflowId}/revisions/${increment}/restore`,
    );
    return response.data;
}
