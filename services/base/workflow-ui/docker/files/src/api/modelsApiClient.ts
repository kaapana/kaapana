import axios from 'axios'

// Create a separate client for kaapana-backend
const backendClient = axios.create({
    baseURL: import.meta.env.VITE_KAAPANA_BACKEND_URL || "/kaapana-backend/",
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

backendClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('Kaapana Backend API Error:', error)
        return Promise.reject(error)
    }
)

export interface InstalledModel {
    id: number
    project_id: string
    friendly_name: string
    models_name: string
    task_ids: string
    description: string
    targets: string[]
    input_modalities: string[]
}

export async function fetchInstalledModels(kind?: string): Promise<InstalledModel[]> {
    const params: any = {}
    if (kind !== undefined) {
        params.kind = kind
    }

    const response = await backendClient.get<InstalledModel[]>('/client/installed_models', { params })
    return response.data
}
