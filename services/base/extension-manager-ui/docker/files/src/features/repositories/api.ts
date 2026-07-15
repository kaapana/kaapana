import apiClient from '@/shared/api/client'
import type {
  CreateRepositoryRequest,
  ExtensionManifestResponse,
  Repository,
  UpdateRepositoryRequest,
} from '@/shared/types/apiSchemas'
import type { ExtensionManifestFilters } from '@/features/catalog/types'

const API_BASE = '/repositories'

export async function fetchRepositories(): Promise<Repository[]> {
  const response = await apiClient.get<Repository[]>(API_BASE)
  if (!response.data || !Array.isArray(response.data)) {
    return []
  }
  return response.data
}

export async function createRepository(repository: CreateRepositoryRequest): Promise<Repository> {
  const response = await apiClient.post<Repository>(API_BASE, repository)
  return response.data
}

export async function fetchRepositoryById(repositoryId: string): Promise<Repository> {
  const response = await apiClient.get<Repository>(`${API_BASE}/${repositoryId}`)
  return response.data
}

export async function updateRepository(
  repositoryId: string,
  repository: UpdateRepositoryRequest,
): Promise<Repository> {
  const response = await apiClient.put<Repository>(`${API_BASE}/${repositoryId}`, repository)
  return response.data
}

export async function deleteRepository(repositoryId: string): Promise<void> {
  await apiClient.delete(`${API_BASE}/${repositoryId}`)
}

export async function fetchRepositoryExtensionTags(repositoryId: string): Promise<string[]> {
  const response = await apiClient.get(`${API_BASE}/${repositoryId}/extensions`)
  if (!response.data || !Array.isArray(response.data)) {
    return []
  }
  return response.data
}

export async function fetchRepositoryExtensionManifests(
  repositoryId: string,
  filters: ExtensionManifestFilters = {},
): Promise<ExtensionManifestResponse[]> {
  const params = {
    tags: filters.tags?.join(','),
  }
  const response = await apiClient.get<ExtensionManifestResponse[]>(
    `${API_BASE}/${repositoryId}/extensionManifests`,
    {
      params,
    },
  )
  if (!response.data || !Array.isArray(response.data)) {
    return []
  }
  return response.data
}
