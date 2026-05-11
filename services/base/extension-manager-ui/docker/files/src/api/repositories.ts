import apiClient from './extensionManagerApiClient';
import type {
    CreateRepositoryRequest,
    ExtensionManifest,
    ExtensionManifestFilters,
    Repository,
    UpdateRepositoryRequest,
} from '@/types/schemas';

const API_BASE = '/repositories'


export async function fetchRepositories(): Promise<Repository[]> {
    const response = await apiClient.get<Repository[]>(API_BASE);
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}

export async function createRepository(repository: CreateRepositoryRequest): Promise<Repository> {
    const response = await apiClient.post<Repository>(API_BASE, repository);
    return response.data;
}

export async function fetchRepositoryById(repositoryId: string): Promise<Repository> {
    const response = await apiClient.get<Repository>(`${API_BASE}/${repositoryId}`);
    return response.data;
}

export async function updateRepository(repositoryId: string, repository: UpdateRepositoryRequest): Promise<Repository> {
    const response = await apiClient.put<Repository>(`${API_BASE}/${repositoryId}`, repository);
    return response.data;
}

export async function deleteRepository(repositoryId: string): Promise<void> {
    await apiClient.delete(`${API_BASE}/${repositoryId}`);
}

export async function fetchRepositoryExtensionTags(repositoryId: string): Promise<string[]> {
    const response = await apiClient.get(`${API_BASE}/${repositoryId}/extensions`);
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}

export async function fetchRepositoryExtensionManifests(repositoryId: string, filters: ExtensionManifestFilters = {}): Promise<ExtensionManifest[]> {
    const params = {
        tags: filters.tags?.join(','),
        limit: filters.limit,
        skip: filters.skip,
    };
    const response = await apiClient.get(`${API_BASE}/${repositoryId}/extensionManifests`, {
        params,
    });
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}
