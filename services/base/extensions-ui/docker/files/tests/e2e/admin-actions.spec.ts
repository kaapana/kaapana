import { test, expect, type Page } from '@playwright/test'
import { defaultMockData, type MockData } from './fixtures/mock-backend'
import { openView, row } from './fixtures/helpers'

// update-extensions, filepond-upload and import-container are admin-only under
// the shipped policy; the view HIDES (not disables) the controls that call
// them — see Extensions.vue.

// A claim-holding `user`: reaches the extensions list and can install/delete,
// which is exactly the population data.rego's ^/extensions-ui grant serves.
const claimHolder: MockData = {
  ...defaultMockData,
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
}

const updateControl = (page: Page) => page.getByTestId('update-extensions')
// Upload.vue renders a bare <file-pond>, whose root element carries this class.
const dropZone = (page: Page) => page.locator('.filepond--root')

test('a non-admin sees neither the update control nor the upload drop zone', async ({ page }) => {
  await openView(page, claimHolder)

  // The list itself works, so the absences below are the gating and not a
  // failure to boot.
  await expect(updateControl(page)).toHaveCount(0)
  await expect(dropZone(page)).toHaveCount(0)
  // The install path stays available to a claim holder.
  await expect(row(page, 'JupyterLab').getByRole('button', { name: 'Launch' })).toBeVisible()
})

test('an admin sees both the update control and the upload drop zone', async ({ page }) => {
  await openView(page)

  await expect(updateControl(page)).toBeVisible()
  await expect(dropZone(page)).toBeVisible()
})

// The update endpoint is granted, but only one of the two endpoints the upload
// drop zone needs. Granted for GET, because that is the method the view checks.
const partialGrant: MockData = {
  ...claimHolder,
  policyData: {
    endpoints_per_role: {
      user: [
        ...(claimHolder.policyData.endpoints_per_role.user ?? []),
        { path: '^/kube-helm-api/update-extensions$', methods: ['GET'] },
        { path: '^/kube-helm-api/filepond-upload$', methods: ['GET'] },
      ],
    },
  },
}

test('a partial grant shows only the control it covers', async ({ page }) => {
  await openView(page, partialGrant)

  await expect(updateControl(page)).toBeVisible()
  // The drop zone also needs import-container, which is not granted.
  await expect(dropZone(page)).toHaveCount(0)
})

test('an unloaded policy hides the admin-only controls (fail closed)', async ({ page }) => {
  // The policy endpoint fails, so the store keeps its empty default.
  await openView(page, defaultMockData, {
    routes: (p) => p.route('**/kaapana-backend/open-policy-data', (r) => r.fulfill({ status: 503 })),
  })

  await expect(updateControl(page)).toHaveCount(0)
  await expect(dropZone(page)).toHaveCount(0)
})
