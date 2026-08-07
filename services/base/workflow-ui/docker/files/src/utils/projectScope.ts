import type { InternalAxiosRequestConfig } from 'axios'

// Inlined mirror of @kaapana/base-ui's selectedProject/httpClient helpers —
// this view does not depend on the library, so keep these in step with it.
//
// The shell serves the view under /project/<short_id>/; the document URL is
// the single source of the project selection. Served without the prefix,
// calls go out unscoped and the scoped backends answer 400.

/** '/project/<short_id>' document prefix, or '' when served unscoped. */
export function getProjectBase(): string {
  const slug = window.location.pathname.match(/^\/project\/([^/]+)\//)?.[1]
  return slug ? `/project/${slug}` : ''
}

// The services that consume the Project header. Anchored, so an already
// prefixed value is left alone.
const PROJECT_SCOPED = /^\/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)(\/|$)/

/**
 * Project-prefix a client's `baseURL`. The axios clients keep the service root
 * in `baseURL` and pass service-relative paths per call, so the prefix belongs
 * on the baseURL — on `url` it would land after the service segment.
 */
export function prefixProjectScope(
  config: InternalAxiosRequestConfig,
): InternalAxiosRequestConfig {
  if (config.baseURL && PROJECT_SCOPED.test(config.baseURL)) {
    const base = getProjectBase()
    if (base) config.baseURL = `${base}${config.baseURL}`
  }
  return config
}
