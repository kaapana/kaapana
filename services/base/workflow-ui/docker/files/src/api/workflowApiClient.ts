import axios from 'axios'
import { prefixProjectScope } from '@/utils/projectScope'


const apiClient = axios.create({
    baseURL: import.meta.env.VITE_WORKFLOW_API_URL + "/v1",
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// workflow-api's POST /workflow-runs requires the trusted Project header, and
// auth-backend only injects it for a /project/<short_id>/ URL.
apiClient.interceptors.request.use(prefixProjectScope)

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error)
        return Promise.reject(error)
    }
)

export default apiClient