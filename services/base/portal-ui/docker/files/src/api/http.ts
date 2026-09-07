import axios from 'axios'

// Single shared axios instance; all backend routes are same-origin behind Traefik.
const http = axios.create({
  timeout: 10000,
})

// Calls to these services are rewritten onto the platform-wide
// /project/<short_id>/<service>/... convention (traefik strips the prefix,
// auth-backend authorizes it). The slug comes from the document URL — not
// localStorage, which other tabs rewrite and would cross-tab mis-scope calls.
const PROJECT_SCOPED = /^\/(kaapana-backend|kube-helm-api|workflow-api|dicom-web-filter)\//

http.interceptors.request.use((config) => {
  if (config.url && PROJECT_SCOPED.test(config.url)) {
    const slug = location.pathname.match(/^\/project\/([^/]+)(\/|$)/)?.[1]
    if (slug) config.url = `/project/${slug}${config.url}`
  }
  return config
})

// oauth2-proxy 302s an expired session to Keycloak on the SAME host, so it
// surfaces as a followed redirect into the auth path or as login HTML where
// JSON was expected. A dedicated Keycloak host would be cross-origin —
// undetectable here, degrading harmlessly to a plain request failure.
const KEYCLOAK_AUTH_PATH = /\/auth\/realms\/.*\/protocol\/openid-connect\/auth/

export function isKeycloakAuthUrl(url: string | null | undefined): boolean {
  return !!url && KEYCLOAK_AUTH_PATH.test(url)
}

// Reload the shell as a top-level request: the proxy redirects it to login and
// back. The module-level re-entrancy guard resets on every load, so an endpoint
// that legitimately returns 401 would reload-loop the shell; the sessionStorage
// stamp suppresses repeat auto-reloads within the backoff window.
export const LOGIN_RELOAD_BACKOFF_MS = 30_000
const LOGIN_RELOAD_STAMP_KEY = 'kaapana:lastLoginReload'

let loginReloadTriggered = false
export function reloadForLogin(): void {
  if (loginReloadTriggered) return
  const last = Number(sessionStorage.getItem(LOGIN_RELOAD_STAMP_KEY)) || 0
  const now = Date.now()
  if (now - last < LOGIN_RELOAD_BACKOFF_MS) {
    console.warn(
      `Suppressed login reload: the last one was ${Math.round((now - last) / 1000)}s ago ` +
        '(an endpoint may be returning 401 for a logged-in session)',
    )
    return
  }
  loginReloadTriggered = true
  sessionStorage.setItem(LOGIN_RELOAD_STAMP_KEY, String(now))
  window.location.reload()
}

// XHR follows the proxy's 302 transparently, so an expired session surfaces as
// a response whose final URL is the Keycloak auth path, or as a 401. A plain
// text/html body is deliberately NOT treated as expired: static assets fall
// back to an HTML page on 404, which would reload-loop the shell.
http.interceptors.response.use(
  (response) => {
    if (isKeycloakAuthUrl(response.request?.responseURL)) {
      reloadForLogin()
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401 || isKeycloakAuthUrl(error.request?.responseURL)) {
      reloadForLogin()
    }
    return Promise.reject(error)
  },
)

export default http
