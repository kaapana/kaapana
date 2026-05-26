import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_EXTENSION_MANAGER_API_URL ?? '/extensions-api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response: any) => response,
  (error: any) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  },
)

export default apiClient
