import { test, expect, type Page } from '@playwright/test'
import type { UserItem } from '@/common/types'
import type { UserRight } from '@/permissions/permissions.store'
import {
  defaultMockData,
  RESEARCH_PROJECT,
  SCIENTIST_USER,
  type MockData,
} from './fixtures/mock-backend'
import { expandSection, openProject, row } from './fixtures/helpers'

const PROJECT_MANAGER: UserItem = {
  ...SCIENTIST_USER,
  id: '00000000-0000-0000-0000-000000000010',
  username: 'grace',
  first_name: 'Grace',
  last_name: 'Hopper',
  realm_roles: ['project-manager', 'user'],
}

function right(name: string): UserRight {
  return { name, description: '', claim_key: '', claim_value: '', project_id: RESEARCH_PROJECT.id }
}

function as(user: UserItem, rights: UserRight[] = []): MockData {
  return {
    ...defaultMockData,
    currentUser: user,
    rights,
    users: [...defaultMockData.users, PROJECT_MANAGER],
  }
}

const sections = (page: Page) => page.getByRole('heading', { level: 2 })
const section = (page: Page, name: string) => page.getByRole('heading', { level: 2, name })

test('an admin gets every section and control', async ({ page }) => {
  await openProject(page, RESEARCH_PROJECT)

  await expect(sections(page)).toHaveText([
    'Project members',
    'Project workflows',
    'Multiinstallable applications',
    'Active project applications',
  ])
  await expect(page.getByRole('button', { name: 'Add members' })).toBeVisible()
  await expandSection(page, 'Multiinstallable applications')
  await expect(row(page, 'Tensorboard').getByRole('button', { name: 'Launch' })).toBeEnabled()
})

test('a project manager administers members and whitelists but not applications', async ({
  page,
}) => {
  await openProject(page, RESEARCH_PROJECT, as(PROJECT_MANAGER))

  // The gateway policy grants kube-helm's extensions, install and delete to admins only.
  await expect(sections(page)).toHaveText([
    'Project members',
    'Project workflows',
    'Active project applications',
  ])
  await expect(page.getByRole('button', { name: 'Add members' })).toBeVisible()
  await expandSection(page, 'Project workflows')
  await expect(row(page, 'nnunet-predict').getByRole('checkbox')).toBeEnabled()
  await expandSection(page, 'Active project applications')
  await expect(
    page.getByRole('button', { name: 'Uninstall JupyterLab (notebooks)' }),
  ).toBeDisabled()
})

test('a user without project rights only sees the project', async ({ page }) => {
  await openProject(page, RESEARCH_PROJECT, as(SCIENTIST_USER))

  await expect(sections(page)).toHaveText([
    'Project members',
    'Project workflows',
    'Active project applications',
  ])
  await expect(page.getByRole('button', { name: 'Add members' })).toHaveCount(0)
  await expandSection(page, 'Project members')
  await expect(
    row(page, SCIENTIST_USER.username).getByRole('button', {
      name: `Remove ${SCIENTIST_USER.username} from the project`,
    }),
  ).toHaveCount(0)
})

test('a user with AII rights gets the controls those rights cover', async ({ page }) => {
  await openProject(
    page,
    RESEARCH_PROJECT,
    as(SCIENTIST_USER, [
      right('view_applications'),
      right('launch_application'),
      right('manage_users'),
    ]),
  )

  await expect(section(page, 'Multiinstallable applications')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Add members' })).toBeVisible()
  await expandSection(page, 'Multiinstallable applications')
  await expect(row(page, 'Tensorboard').getByRole('button', { name: 'Launch' })).toBeEnabled()
})

test('without the policy data, role grants allow nothing', async ({ page }) => {
  const policy = page.waitForResponse((r) => r.url().endsWith('/open-policy-data'))
  await openProject(page, RESEARCH_PROJECT, { ...defaultMockData, policyData: {} })
  await policy
  // Rendered from the loaded user, so the policy has been applied by now too.
  await expect(page.getByRole('button', { name: 'Delete project' })).toBeVisible()

  await expect(section(page, 'Multiinstallable applications')).toHaveCount(0)
})
