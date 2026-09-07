import axios from 'axios'
import { prefixProjectScope } from '@/utils/projectScope'

const backendClient = axios.create({
    baseURL: import.meta.env.VITE_KAAPANA_BACKEND_URL || "/kaapana-backend/",
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// /client/dataset(s) both Depends(get_project), so an unprefixed call is a 400.
backendClient.interceptors.request.use(prefixProjectScope)

backendClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('Kaapana Backend API Error:', error)
        return Promise.reject(error)
    }
)

export interface Dataset {
    name: string
    time_created: string
    time_updated: string
    username: string
    identifiers: string[]
}

export async function fetchDatasets(limit?: number): Promise<Dataset[]> {
    const params: any = {}
    if (limit !== undefined) {
        params.limit = limit
    }

    const response = await backendClient.get<Dataset[]>('/client/datasets', { params })
    return response.data
}

export async function fetchDataset(datasetName: string): Promise<Dataset> {
    const response = await backendClient.get<Dataset>('/client/dataset', {
        params: { instance_name: datasetName }
    })
    return response.data
}
