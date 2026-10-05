import { httpClient } from '@kaapana/base-ui'
import { EXTENSIONS_API, asList } from '@/shared/api/extensionsApi'
import type { InstalledExtension } from '@/shared/types/apiSchemas'

const API_BASE = `${EXTENSIONS_API}/extensions`

export async function installExtension(
  repositoryId: string,
  tag: string,
): Promise<InstalledExtension> {
  const response = await httpClient.post<InstalledExtension>(`${API_BASE}/install`, null, {
    params: { repository_id: repositoryId, tag },
  })
  return response.data
}

export async function fetchExtensions(): Promise<InstalledExtension[]> {
  const response = await httpClient.get(API_BASE)
  return asList<InstalledExtension>(response.data)
}

export async function uninstallExtension(extensionId: string): Promise<void> {
  await httpClient.post(`${API_BASE}/${extensionId}/uninstall`)
}
