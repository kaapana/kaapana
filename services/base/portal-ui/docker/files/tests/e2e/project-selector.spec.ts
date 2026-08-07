import { test, expect, type Locator } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

// toBeVisible() passes on line-clamped text (a non-empty bounding box is
// enough), so assert the role line's box lies fully inside the option's box —
// Vuetify's one-line subtitle clamp pushes a clipped line below it.
async function expectRoleShown(option: Locator, role: string) {
  const roleLine = option.getByText(role)
  await expect(roleLine).toBeVisible()
  const roleBox = await roleLine.boundingBox()
  const optionBox = await option.boundingBox()
  expect(roleBox).toBeTruthy()
  expect(optionBox).toBeTruthy()
  expect(roleBox!.y).toBeGreaterThanOrEqual(optionBox!.y)
  expect(roleBox!.y + roleBox!.height).toBeLessThanOrEqual(optionBox!.y + optionBox!.height + 0.5)
}

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await stubView(page, '/data-gallery-ui')
})

test('lists the available projects and pre-selects the first one', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByLabel('Project')).toBeVisible()
  await page.locator('.project-select .v-field__input').click()
  // ^-anchored: every option's subtitle carries "Your Role: admin" here.
  await expect(page.getByRole('option', { name: /^admin/ })).toBeVisible()
  await expect(page.getByRole('option', { name: /research-b/ })).toBeVisible()
})

test('switching project updates the URL and reloads the iframe under the new prefix', async ({
  page,
}) => {
  // A leftover cookie from a pre-URL-scoping session must be cleared on switch.
  await page.context().addCookies([{ name: 'Project', value: 'stale', url: 'http://localhost:4300' }])
  await page.goto('/')
  await expect(page.frameLocator('iframe.kaapana-iframe').locator('body')).toHaveAttribute(
    'data-stub',
    'data-gallery-ui',
  )

  await page.locator('.project-select .v-field__input').click()
  await page.getByRole('option', { name: /research-b/ }).click()

  await expect(page).toHaveURL(/\/project\/resb/)
  await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
    'src',
    '/project/resb/data-gallery-ui',
  )

  // localStorage['project'] is only the shell's new-tab default.
  const stored = await page.evaluate(() => JSON.parse(localStorage['project']))
  expect(stored.name).toBe('research-b')

  // The legacy Project cookie is gone entirely (leftovers actively cleared).
  await expect
    .poll(async () => (await page.context().cookies()).find((c) => c.name === 'Project'))
    .toBeUndefined()
})

test('archived projects show an "Archived" chip in the dropdown', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    projects: [
      { id: 1, name: 'admin', short_id: 'admin' },
      { id: 2, name: 'old-study', short_id: 'old', is_archived: true },
    ],
  })
  await page.goto('/')
  await page.locator('.project-select .v-field__input').click()
  const archivedOption = page.getByRole('option', { name: /old-study/ })
  await expect(archivedOption.getByText('Archived')).toBeVisible()
})

test('admin fetches all projects from /aii/projects', async ({ page }) => {
  const req = page.waitForRequest('**/aii/projects')
  await page.goto('/')
  await req
})

test('a non-admin fetches only their own projects', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    aiiUser: { id: '00000000-0000-0000-0000-000000000001', realm_roles: ['user'] },
  })
  const req = page.waitForRequest(
    '**/aii/users/00000000-0000-0000-0000-000000000001/projects',
  )
  await page.goto('/')
  await req
})

test('dropdown items show the caller\'s per-project role from the per-user listing', async ({
  page,
}) => {
  // Non-admin: /aii/users/<id>/projects carries role_name per membership.
  await installMockBackend(page, {
    ...defaultMockData,
    aiiUser: { id: '00000000-0000-0000-0000-000000000001', realm_roles: ['user'] },
    projects: [
      { id: 1, name: 'admin', short_id: 'admin', role_name: 'member' },
      { id: 2, name: 'research-b', short_id: 'resb', role_name: 'data-scientist' },
    ],
  })
  await page.goto('/')
  await page.locator('.project-select .v-field__input').click()
  await expectRoleShown(page.getByRole('option', { name: /^admin/ }), 'Your Role: member')
  await expectRoleShown(
    page.getByRole('option', { name: /research-b/ }),
    'Your Role: data-scientist',
  )
})

test('admins see their global admin role on every project', async ({ page }) => {
  // The all-projects listing (/aii/projects) has no membership info; the shell
  // derives "admin" from the realm role, matching the gateway's scoping rule.
  await page.goto('/')
  await page.locator('.project-select .v-field__input').click()
  await expectRoleShown(page.getByRole('option', { name: /^admin/ }), 'Your Role: admin')
  await expectRoleShown(page.getByRole('option', { name: /research-b/ }), 'Your Role: admin')
})
