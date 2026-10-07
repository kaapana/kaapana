import { test, expect, type Page } from '@playwright/test'
import type { UserItem } from '@/common/types'
import {
  defaultMockData,
  installMockBackend,
  SCIENTIST_USER,
  type MockData,
} from './fixtures/mock-backend'
import { confirmAction, dialog, row } from './fixtures/helpers'

const RIGHTS_PATH = '/projects-ui/role-rights'

async function open(page: Page, data: MockData = defaultMockData) {
  const state = await installMockBackend(page, data)
  await page.goto(RIGHTS_PATH)
  await expect(page.getByText('manage_users', { exact: true })).toBeVisible()
  return state
}

test('sends users who cannot change role rights back to the project list', async ({ page }) => {
  await installMockBackend(page, { ...defaultMockData, currentUser: SCIENTIST_USER })
  await page.goto(RIGHTS_PATH)

  await expect(page).toHaveURL(/\/projects-ui\/$/)
  await expect(page.getByRole('heading', { name: 'Edit Role Rights' })).toHaveCount(0)
})

test('a project manager may change role rights', async ({ page }) => {
  const manager: UserItem = { ...SCIENTIST_USER, realm_roles: ['project-manager', 'user'] }
  await open(page, { ...defaultMockData, currentUser: manager })

  await expect(page.getByRole('button', { name: 'Add Right' })).toBeVisible()
})

test('saves staged role-right changes', async ({ page }) => {
  const state = await open(page)
  // Scientist (role 3) gains manage_users (right 1).
  await row(page, 'manage_users').getByRole('checkbox').nth(2).click()
  await expect(page.getByText('1 unsaved change')).toBeVisible()

  await page.getByRole('button', { name: 'Save Changes' }).click()
  await confirmAction(page, 'Save changes')

  await expect(page.getByText('unsaved change')).toHaveCount(0)
  expect(state.roleRights[3]).toEqual(expect.arrayContaining([1, 2]))
})

test('discards staged role-right changes', async ({ page }) => {
  const state = await open(page)
  const checkbox = row(page, 'manage_users').getByRole('checkbox').nth(2)
  await checkbox.click()
  await expect(page.getByText('1 unsaved change')).toBeVisible()

  await page.getByRole('button', { name: 'Discard' }).click()

  await expect(page.getByText('unsaved change')).toHaveCount(0)
  await expect(checkbox).not.toBeChecked()
  expect(state.roleRights[3]).not.toContain(1)
})

test('adds a right after validating every field', async ({ page }) => {
  const state = await open(page)
  await page.getByRole('button', { name: 'Add Right' }).click()
  const form = dialog(page)
  const sent: string[] = []
  page.on('request', (r) => r.method() === 'POST' && sent.push(r.url()))

  await form.getByRole('button', { name: 'Add right' }).click()
  for (const message of [
    'Enter a name for the right, such as manage_users.',
    'Enter a description.',
    'Enter the JWT claim key.',
    'Enter the JWT claim value.',
  ]) {
    await expect(form.getByText(message)).toBeVisible()
  }
  expect(sent).toEqual([])

  await form.getByLabel('Name', { exact: true }).fill('export_data')
  await form.getByLabel('Description').fill('Export project data')
  await form.getByLabel('JWT claim key').fill('kaapana.ai/export')
  await form.getByLabel('JWT claim value').fill('export')
  await form.getByRole('button', { name: 'Add right' }).click()

  await expect(form).toBeHidden()
  await expect(page.getByText('export_data', { exact: true })).toBeVisible()
  expect(state.rightsCatalogue.map((r) => r.name)).toContain('export_data')
})
