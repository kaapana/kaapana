import axios from 'axios'
import type { AxiosError, AxiosResponse } from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_EXTENSION_MANAGER_API_URL ?? '/extensions-api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  },
)

export default apiClient
