import apiClient from './extensionManagerApiClient';
import type { Extension } from '@/types/schemas';

const API_BASE = '/extensions'

export async function installExtension(repositoryId: string, tag: string): Promise<void> {
    await apiClient.post(`${API_BASE}/install`, {
        repositoryId,
        tag,
    });
}

export async function fetchExtensions(): Promise<Extension[]> {
    const response = await apiClient.get<Extension[]>(API_BASE);
    if (!response.data || !Array.isArray(response.data)) {
        return [];
    }
    return response.data;
}

export async function fetchExtensionById(extensionId: string): Promise<Extension> {
    const response = await apiClient.get<Extension>(`${API_BASE}/${extensionId}`);
    return response.data;
}

export async function uninstallExtension(extensionId: string, repositoryId: string): Promise<void> {
    await apiClient.post(`${API_BASE}/uninstall`, {
        extensionId,
        repositoryId,
    });
}

