import { test, expect } from '@playwright/test'
import { installMockBackend, stubView } from './fixtures/mock-backend'

test('the account menu names the user and logs out', async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
  // The logout target is a real top-window navigation; stub it so the assertion
  // is about the navigation and not about what the dev server serves for it.
  await page.route('**/kaapana-backend/oidc-logout', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>bye</body></html>' }),
  )
  await page.goto('/')

  await page.getByRole('button', { name: 'Account' }).click()
  // Vuetify's menu overlay carries no menu role, so scope by its content class.
  const menu = page.locator('.v-overlay__content')
  await expect(menu.getByText('kaapana', { exact: true })).toBeVisible()

  await menu.getByRole('button', { name: 'Log Out' }).click()
  await page.waitForURL('**/kaapana-backend/oidc-logout')
})
