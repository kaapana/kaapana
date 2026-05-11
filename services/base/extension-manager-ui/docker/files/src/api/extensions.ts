import apiClient from './extensionManagerApiClient';
import type { InstalledExtension } from '@/types/schemas';

const API_BASE = '/extensions'

export async function installExtension(repositoryId: string, tag: string): Promise<void> {
    await apiClient.post(`${API_BASE}/install`, null, {
        params: {
            repository_id: repositoryId,
            tag,
        },
    });
}

export async function fetchExtensions(): Promise<InstalledExtension[]> {
    const response = await apiClient.get<InstalledExtension[]>(API_BASE);
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}

export async function fetchExtensionById(extensionId: string): Promise<InstalledExtension> {
    const response = await apiClient.get<InstalledExtension>(`${API_BASE}/${extensionId}`);
    return response.data;
}

export async function uninstallExtension(extensionId: string): Promise<void> {
    await apiClient.post(`${API_BASE}/${extensionId}/uninstall`);
}
