import { test, expect } from '@playwright/test'
import { installMockBackend } from './fixtures/mock-backend'

// The same-host login 302 can render Keycloak inside the shell's iframe;
// IframeHost must detect that and reload the whole window out of it.
test('an iframe landing on the Keycloak auth path triggers a full-window reload', async ({
  page,
}) => {
  await installMockBackend(page)

  // First iframe load 302s to the same-origin Keycloak auth path (expired
  // session); after the shell reloads top-level, the view is served normally.
  let galleryHits = 0
  await page.route('**/data-gallery-ui**', (route) => {
    galleryHits++
    if (galleryHits === 1) {
      return route.fulfill({
        status: 302,
        headers: {
          location: '/auth/realms/kaapana/protocol/openid-connect/auth?client_id=kaapana',
        },
        body: '',
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html><body data-stub="data-gallery-ui">ok</body></html>',
    })
  })
  await page.route('**/auth/realms/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html><body>keycloak login</body></html>',
    }),
  )

  await page.goto('/')

  // The stub only appears after the reload escaped the in-iframe login page.
  // Full reload + iframe reload can exceed the 5s default under parallel-worker
  // load; seen passing at 5.6s.
  await expect(page.frameLocator('iframe.kaapana-iframe').locator('body')).toHaveAttribute(
    'data-stub',
    'data-gallery-ui',
    { timeout: 15_000 },
  )
  expect(galleryHits).toBeGreaterThanOrEqual(2)
})
