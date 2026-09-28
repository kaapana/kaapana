import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  workflowField,
  VIEW_PATH,
} from './fixtures/mock-backend'

// The form's loaders live in @kaapana/base-ui's WorkflowExecution; a failed load
// used to be indistinguishable from an empty backend response.

const fail = (detail: string) => (route: any) =>
  route.fulfill({
    status: 500,
    contentType: 'application/json',
    body: JSON.stringify({ detail }),
  })

test('failing get-ui-form-schemas toasts instead of a silently blank form', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await seedShellState(page)
  await installMockBackend(page)
  await page.route('**/kaapana-backend/client/get-ui-form-schemas', fail('schemas exploded'))
  await page.goto(VIEW_PATH)

  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Failed to load the workflow form')).toBeVisible()
  await expect(toast.getByText('schemas exploded')).toBeVisible()
  // the DAG list comes from another request, so it stays selectable
  await workflowField(page).click()
  await expect(page.getByRole('option', { name: 'mock-all-fields', exact: true })).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

test('failing get-kaapana-instances toasts and still renders the card', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await seedShellState(page)
  await installMockBackend(page)
  await page.route('**/kaapana-backend/client/get-kaapana-instances', fail('no instances'))
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()
  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Failed to load runner instances')).toBeVisible()
  await expect(toast.getByText('no instances')).toBeVisible()
  await expect(page.locator('.v-progress-circular')).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

test('failing get-dags toasts instead of an endless spinner', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await seedShellState(page)
  await installMockBackend(page)
  await page.route('**/kaapana-backend/client/get-dags', fail('dags exploded'))
  await page.goto(VIEW_PATH)

  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Failed to load workflows')).toBeVisible()
  await expect(toast.getByText('dags exploded')).toBeVisible()
  await expect(page.locator('.v-progress-circular')).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

// Toasts take the platform theme's roles instead of the notification library's
// own palette, so they follow dark mode and get the theme's contrasting text.
for (const dark of [false, true]) {
  test(`an error toast uses the ${dark ? 'dark' : 'light'} theme's error colour`, async ({ page }) => {
    await installMockBackend(page)
    await page.addInitScript((d) => localStorage.setItem('settings', JSON.stringify({ darkMode: d })), dark)
    await page.route('**/kaapana-backend/client/get-dags', fail('dags exploded'))
    await page.goto(VIEW_PATH)

    const toast = page.locator('.vue-notification.error', { hasText: 'Failed to load workflows' })
    const themeError = await page.locator('.v-application').evaluate(
      (el) => `rgb(${getComputedStyle(el).getPropertyValue('--v-theme-error').trim().replaceAll(',', ', ')})`,
    )
    await expect(toast).toHaveCSS('background-color', themeError)
  })
}
