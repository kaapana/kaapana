import { test, expect, type Page } from '@playwright/test'
import {
  installMockBackend,
  defaultMockData,
  VIEW_PATH,
  type MockData,
} from './fixtures/mock-backend'

// update-extensions, filepond-upload and import-container are admin-only under
// the shipped policy; the view HIDES (not disables) the controls that call
// them — see Extensions.vue.

function mockData(overrides: Partial<MockData>): MockData {
  return { ...structuredClone(defaultMockData), ...overrides }
}

// A claim-holding `user`: reaches the extensions list and can install/delete,
// which is exactly the population data.rego's ^/extensions-ui grant serves.
const claimHolder = mockData({
  userinfo: { ...defaultMockData.userinfo, groups: ['role:user', '/kaapana_user'] },
  currentUser: { ...defaultMockData.currentUser, realm_roles: ['user'] },
  policyData: {
    endpoints_per_role: {
      user: [
        { path: '^/extensions-ui', methods: ['GET', 'POST', 'PUT', 'DELETE'] },
        { path: '^/kube-helm-api/extensions$', methods: ['GET'] },
        { path: '^/kube-helm-api/helm-install-chart$', methods: ['POST'] },
        { path: '^/kube-helm-api/helm-delete-chart$', methods: ['POST'] },
      ],
    },
  },
})

const updateControl = (page: Page) => page.getByTestId('update-extensions')
// Upload.vue renders a bare <file-pond>, whose root element carries this class.
const dropZone = (page: Page) => page.locator('.filepond--root')

test('a non-admin sees neither the update control nor the upload drop zone', async ({ page }) => {
  await installMockBackend(page, claimHolder)
  await page.goto(VIEW_PATH)

  // The list itself works, so the absences below are the gating and not a
  // failure to boot.
  await expect(page.getByText('MITK Workbench')).toBeVisible()
  await expect(updateControl(page)).toHaveCount(0)
  await expect(dropZone(page)).toHaveCount(0)
  // The install path stays available to a claim holder.
  await expect(page.getByRole('button', { name: 'Launch' }).first()).toBeVisible()
})

test('an admin sees both the update control and the upload drop zone', async ({ page }) => {
  await installMockBackend(page, defaultMockData)
  await page.goto(VIEW_PATH)

  await expect(page.getByText('MITK Workbench')).toBeVisible()
  await expect(updateControl(page)).toBeVisible()
  await expect(dropZone(page)).toBeVisible()
})

test('an unloaded policy hides the admin-only controls (fail closed)', async ({ page }) => {
  await installMockBackend(page, defaultMockData)
  // The policy endpoint fails, so the store keeps its empty default.
  await page.route('**/kaapana-backend/open-policy-data', (r) => r.fulfill({ status: 503 }))
  await page.goto(VIEW_PATH)

  await expect(page.getByText('MITK Workbench')).toBeVisible()
  await expect(updateControl(page)).toHaveCount(0)
  await expect(dropZone(page)).toHaveCount(0)
})
