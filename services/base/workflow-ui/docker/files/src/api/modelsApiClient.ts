import axios from 'axios'
import { prefixProjectScope } from '@/utils/projectScope'
import type { InstalledModel } from '@/types/schemas'

const backendClient = axios.create({
    baseURL: import.meta.env.VITE_KAAPANA_BACKEND_URL || "/kaapana-backend/",
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// The project prefix makes the gateway add the Project header.
// kaapana-backend rejects requests without this header with status 400.
backendClient.interceptors.request.use(prefixProjectScope)

backendClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('Kaapana Backend API Error:', error)
        return Promise.reject(error)
    }
)

export async function fetchInstalledModels(kind?: string): Promise<InstalledModel[]> {
    const params: Record<string, string> = {}
    if (kind !== undefined) {
        params.kind = kind
    }

    const response = await backendClient.get<InstalledModel[]>('/client/installed_models', { params })
    return response.data
}
