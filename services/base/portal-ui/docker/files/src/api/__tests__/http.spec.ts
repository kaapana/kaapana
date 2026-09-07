import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import type { AxiosResponse } from 'axios'

// The reload-on-expired-session helper carries a module-level once-guard, so
// each case loads a fresh copy of the module (vi.resetModules + dynamic import).
describe('http response interceptor (expired session)', () => {
  const realLocation = window.location
  let reload: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.resetModules()
    // The backoff stamp survives page loads by design; tests must not.
    sessionStorage.clear()
    reload = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...realLocation, pathname: '/', href: 'http://localhost/', reload },
    })
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: realLocation })
    vi.restoreAllMocks()
  })

  async function loadHttp() {
    return (await import('@/api/http')).default
  }

  function fulfill(res: Partial<AxiosResponse> & { request?: unknown }) {
    return async (config: unknown) =>
      ({ data: {}, status: 200, statusText: 'OK', headers: {}, config, ...res }) as never
  }

  it('reloads when the request was redirected into the Keycloak auth path', async () => {
    const http = await loadHttp()
    http.defaults.adapter = fulfill({
      // The followed 302 landed on the login page: HTML body, auth-path URL.
      data: '<html>login</html>',
      headers: { 'content-type': 'text/html' },
      request: {
        responseURL:
          'http://localhost/auth/realms/kaapana/protocol/openid-connect/auth?client_id=x',
      },
    })
    await http.get('/aii/projects')
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('does NOT reload on an HTML body that is not the auth page (static-file fallback)', async () => {
    // A missing /jsons/commonData.json falls back to index.html (dev) / an nginx
    // 404 page (prod): HTML, but NOT an expired session. Must not reload-loop.
    const http = await loadHttp()
    http.defaults.adapter = fulfill({
      data: '<!doctype html><html></html>',
      headers: { 'content-type': 'text/html' },
      request: { responseURL: 'http://localhost/jsons/commonData.json' },
    })
    await http.get('/jsons/commonData.json')
    expect(reload).not.toHaveBeenCalled()
  })

  it('reloads on a 401', async () => {
    const http = await loadHttp()
    http.defaults.adapter = async (config) => {
      const err = new Error('unauthorized') as Error & Record<string, unknown>
      err.config = config
      err.request = {}
      err.response = { status: 401, data: {}, statusText: '', headers: {}, config, request: {} }
      throw err
    }
    await expect(http.get('/kaapana-backend/settings')).rejects.toBeTruthy()
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('does NOT reload on a normal JSON response', async () => {
    const http = await loadHttp()
    http.defaults.adapter = fulfill({
      data: { ok: true },
      headers: { 'content-type': 'application/json' },
      request: { responseURL: 'http://localhost/portal-api/menu' },
    })
    await http.get('/portal-api/menu')
    expect(reload).not.toHaveBeenCalled()
  })

  it('fires the reload only once even across several bad responses', async () => {
    const http = await loadHttp()
    http.defaults.adapter = fulfill({
      request: {
        responseURL:
          'http://localhost/auth/realms/kaapana/protocol/openid-connect/auth?client_id=x',
      },
    })
    await http.get('/portal-api/menu')
    await http.get('/aii/projects')
    expect(reload).toHaveBeenCalledTimes(1)
  })

  // The module-level once-guard resets on every page load; an endpoint that
  // legitimately 401s would reload-loop the shell without the sessionStorage
  // backoff. A vi.resetModules + re-import stands in for the page reload.
  describe('reload backoff', () => {
    const authResponse = () =>
      fulfill({
        request: {
          responseURL:
            'http://localhost/auth/realms/kaapana/protocol/openid-connect/auth?client_id=x',
        },
      })

    it('suppresses (and warns about) a second auto-reload within the backoff window', async () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
      let http = await loadHttp()
      http.defaults.adapter = authResponse()
      await http.get('/portal-api/menu')
      expect(reload).toHaveBeenCalledTimes(1)

      // The reload happens: fresh module state, but sessionStorage survives.
      vi.resetModules()
      http = await loadHttp()
      http.defaults.adapter = authResponse()
      await http.get('/portal-api/menu')
      expect(reload).toHaveBeenCalledTimes(1)
      expect(warn).toHaveBeenCalledWith(expect.stringContaining('Suppressed login reload'))
    })

    it('reloads again once the backoff window has expired', async () => {
      const { LOGIN_RELOAD_BACKOFF_MS } = await import('@/api/http')
      sessionStorage.setItem(
        'kaapana:lastLoginReload',
        String(Date.now() - LOGIN_RELOAD_BACKOFF_MS - 1000),
      )
      const http = await loadHttp()
      http.defaults.adapter = authResponse()
      await http.get('/portal-api/menu')
      expect(reload).toHaveBeenCalledTimes(1)
    })
  })
})
