import apiClient from './workflowApiClient';
import type { Workflow } from '@/types/schemas';


// Fetch all workflows
export async function fetchWorkflows(): Promise<Workflow[]> {
    const response = await apiClient.get<Workflow[]>('/workflows');
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}

// Fetch a single workflow by ID
export async function fetchWorkflowById(id: number): Promise<Workflow> {
    const response = await apiClient.get<Workflow>(`/workflows/${id}`);
    return response.data;
}

// Create a new workflow
export async function createWorkflow(workflow: Partial<Workflow>): Promise<Workflow> {
    const response = await apiClient.post<Workflow>('/workflows', workflow);
    return response.data;
}

// Fetch tasks for a workflow increment
export async function fetchWorkflowTasks(title: string, increment: number) {
    const encodedTitle = encodeURIComponent(title)
    const response = await apiClient.get(`/workflows/${encodedTitle}/${increment}/tasks`)
    return response.data
}