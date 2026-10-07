import { test, expect } from '@playwright/test'
import type { UserItem } from '@/common/types'
import {
  CANDIDATE_USER,
  defaultMockData,
  RESEARCH_PROJECT,
  SCIENTIST_USER,
  SYSTEM_USER,
  ADMIN_PROJECT,
} from './fixtures/mock-backend'
import {
  confirmAction,
  dialog,
  expandSection,
  nextRequest,
  openProject,
  row,
  toasts,
} from './fixtures/helpers'

async function open(page: import('@playwright/test').Page) {
  await openProject(page, RESEARCH_PROJECT)
  await expandSection(page, 'Project Users')
}

test('lists the members with their project role', async ({ page }) => {
  await open(page)
  await expect(row(page, SCIENTIST_USER.username)).toContainText('scientist')
  await expect(row(page, 'kaapana')).toContainText('admin')
})

test('a search that matches no member says so and can be cleared', async ({ page }) => {
  await open(page)
  await page.getByRole('textbox', { name: 'Search users' }).fill('nobody')

  await expect(page.getByText('No members match "nobody"')).toBeVisible()
  await page.getByRole('button', { name: 'Clear search', exact: true }).click()
  await expect(row(page, SCIENTIST_USER.username)).toBeVisible()
})

test('adds a user with the chosen role', async ({ page }) => {
  await open(page)
  await page.getByRole('button', { name: 'Add User' }).click()
  const form = dialog(page)
  await form.getByRole('combobox', { name: 'Search and select users' }).click()
  await page.getByRole('option', { name: /Alan Turing/ }).click()
  await page.keyboard.press('Escape')
  await form.getByText('principal-investigator', { exact: true }).click()

  const request = nextRequest(page, 'POST', `/user/${CANDIDATE_USER.id}`)
  await form.getByRole('button', { name: 'Add User' }).click()
  expect(new URL((await request).url()).pathname).toBe(
    `/aii/projects/${RESEARCH_PROJECT.id}/role/principal-investigator/user/${CANDIDATE_USER.id}`,
  )

  await expect(form).toBeHidden()
  await expect(row(page, CANDIDATE_USER.username)).toContainText('principal-investigator')
  await expect(toasts(page)).toContainText(
    '1 user added as "principal-investigator". Access starts within a few minutes.',
  )
})

test('finds users to add by name, not only by username', async ({ page }) => {
  const grace: UserItem = {
    ...CANDIDATE_USER,
    id: '00000000-0000-0000-0000-000000000030',
    username: 'grace',
    first_name: 'Grace',
    last_name: 'Hopper',
    email: 'grace@example.org',
  }
  await openProject(page, RESEARCH_PROJECT, {
    ...defaultMockData,
    users: [...defaultMockData.users, grace],
  })
  await expandSection(page, 'Project Users')
  await page.getByRole('button', { name: 'Add User' }).click()
  const search = dialog(page).getByRole('combobox', { name: 'Search and select users' })

  await search.fill('turing')
  await expect(page.getByRole('option')).toHaveText([/Alan Turing/])
  await search.fill('grace hop')
  await expect(page.getByRole('option')).toHaveText([/Grace Hopper/])
})

test("changes a member's role", async ({ page }) => {
  await open(page)
  await row(page, SCIENTIST_USER.username)
    .getByRole('button', { name: `Change role of ${SCIENTIST_USER.username}` })
    .click()
  await dialog(page).getByText('principal-investigator', { exact: true }).click()

  const request = nextRequest(page, 'PUT', '/rolemapping')
  await dialog(page).getByRole('button', { name: 'Save Changes' }).click()
  expect(new URL((await request).url()).searchParams.get('role_name')).toBe(
    'principal-investigator',
  )
  await expect(row(page, SCIENTIST_USER.username)).toContainText('principal-investigator')
  await expect(toasts(page)).toContainText(
    `@${SCIENTIST_USER.username} is now "principal-investigator". The change applies within a few minutes.`,
  )
})

test('removes a member', async ({ page }) => {
  await open(page)
  await row(page, SCIENTIST_USER.username)
    .getByRole('button', { name: `Remove ${SCIENTIST_USER.username} from the project` })
    .click()
  await confirmAction(page, 'Remove user')

  await expect(row(page, SCIENTIST_USER.username)).toHaveCount(0)
  await expect(toasts(page)).toContainText(`@${SCIENTIST_USER.username} removed from the project.`)
})

test('hides system users unless asked to show them', async ({ page }) => {
  await openProject(page, ADMIN_PROJECT)
  await expandSection(page, 'Project Users')

  await expect(row(page, SYSTEM_USER.username)).toHaveCount(0)
  await page.getByRole('checkbox', { name: 'Show system users' }).click()
  await expect(row(page, SYSTEM_USER.username)).toBeVisible()
})

test.describe('in an archived project', () => {
  test('members cannot be added, changed or removed', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT, {
      ...defaultMockData,
      projects: [defaultMockData.projects[0], { ...RESEARCH_PROJECT, is_archived: true }],
    })
    await expandSection(page, 'Project Users')
    await expect(page.getByText('This project is archived')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Add User' })).toBeDisabled()
    const ada = row(page, SCIENTIST_USER.username)
    await expect(
      ada.getByRole('button', { name: `Change role of ${SCIENTIST_USER.username}` }),
    ).toBeDisabled()
    await expect(
      ada.getByRole('button', { name: `Remove ${SCIENTIST_USER.username} from the project` }),
    ).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Edit project' })).toHaveCount(0)
  })
})
