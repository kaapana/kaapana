import axios, { type InternalAxiosRequestConfig } from 'axios'
import { getProjectBase } from './selectedProject'

export const httpClient = axios.create({
  headers: {},
  timeout: 10000,
})

export const httpClientWithoutTimeout = axios.create({
  headers: {},
  timeout: 0,
})

// Calls to project-scoped services are rewritten onto the platform-wide
// /project/<short_id>/<service>/... convention; the <short_id> comes from the
// document URL, which carries the same prefix.
const PROJECT_SCOPED = /^\/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

function prefixProjectScope(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  if (config.url && PROJECT_SCOPED.test(config.url)) {
    const base = getProjectBase()
    if (base) config.url = `${base}${config.url}`
  }
  return config
}

httpClient.interceptors.request.use(prefixProjectScope)
httpClientWithoutTimeout.interceptors.request.use(prefixProjectScope)
