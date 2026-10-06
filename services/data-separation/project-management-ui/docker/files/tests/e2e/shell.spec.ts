import { test, expect } from '@playwright/test'
import { RESEARCH_PROJECT } from './fixtures/mock-backend'
import {
  expandSection,
  lastDirty,
  openProject,
  openView,
  recordShellMessages,
  row,
} from './fixtures/helpers'

test('staged role-right changes mark the view dirty until they are undone', async ({ page }) => {
  const messages = await recordShellMessages(page)
  await openView(page)
  await page.getByRole('button', { name: 'Edit Role Rights' }).click()

  await expect.poll(async () => lastDirty(await messages())).toBe(false)
  await row(page, 'manage_users').getByRole('checkbox').nth(2).click()
  await expect.poll(async () => lastDirty(await messages())).toBe(true)
  await row(page, 'manage_users').getByRole('checkbox').nth(2).click()
  await expect.poll(async () => lastDirty(await messages())).toBe(false)
})

test('the project page stays dirty while any section has staged changes', async ({ page }) => {
  const messages = await recordShellMessages(page)
  await openProject(page, RESEARCH_PROJECT)
  await expandSection(page, 'Project Workflows')
  await expandSection(page, 'Multiinstallable Applications')
  const workflows = page.locator('.v-row', {
    has: page.getByRole('heading', { name: 'Project Workflows' }),
  })
  const apps = page.locator('.v-row', {
    has: page.getByRole('heading', { name: 'Multiinstallable Applications' }),
  })

  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  await expect(workflows.getByText('1 unsaved')).toBeVisible()
  await row(page, 'Tensorboard').getByRole('checkbox').click()
  await expect(apps.getByText('1 unsaved')).toBeVisible()
  await expect.poll(async () => lastDirty(await messages())).toBe(true)

  await workflows.getByRole('button', { name: 'Save Changes' }).click()
  await expect(workflows.getByText('unsaved')).toHaveCount(0)
  await expect(apps.getByText('1 unsaved')).toBeVisible()
  expect(lastDirty(await messages())).toBe(true)

  await apps.getByRole('button', { name: 'Discard' }).click()
  await expect.poll(async () => lastDirty(await messages())).toBe(false)
})
