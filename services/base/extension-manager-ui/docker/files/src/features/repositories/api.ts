import { httpClient } from '@kaapana/base-ui'
import { EXTENSIONS_API, asList } from '@/shared/api/extensionsApi'
import type {
  CreateRepositoryRequest,
  ExtensionManifestResponse,
  Repository,
  UpdateRepositoryRequest,
} from '@/shared/types/apiSchemas'

const API_BASE = `${EXTENSIONS_API}/repositories`

export async function fetchRepositories(): Promise<Repository[]> {
  const response = await httpClient.get(API_BASE)
  return asList<Repository>(response.data)
}

export async function createRepository(repository: CreateRepositoryRequest): Promise<Repository> {
  const response = await httpClient.post<Repository>(API_BASE, repository)
  return response.data
}

export async function updateRepository(
  repositoryId: string,
  repository: UpdateRepositoryRequest,
): Promise<Repository> {
  const response = await httpClient.put<Repository>(`${API_BASE}/${repositoryId}`, repository)
  return response.data
}

export async function deleteRepository(repositoryId: string): Promise<void> {
  await httpClient.delete(`${API_BASE}/${repositoryId}`)
}

export async function fetchRepositoryExtensionManifests(
  repositoryId: string,
): Promise<ExtensionManifestResponse[]> {
  const response = await httpClient.get(`${API_BASE}/${repositoryId}/extensionManifests`, {
    timeout: 30_000,
  })
  return asList<ExtensionManifestResponse>(response.data)
}
