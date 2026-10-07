import { test, expect, type Page } from '@playwright/test'
import { RESEARCH_PROJECT } from './fixtures/mock-backend'
import {
  confirmAction,
  dialog,
  discardQuestion,
  expandSection,
  lastDirty,
  openProject,
  openView,
  pressEscapeUntil,
  recordShellMessages,
  row,
} from './fixtures/helpers'

async function stageWorkflowChange(page: Page) {
  await openProject(page, RESEARCH_PROJECT)
  await expandSection(page, 'Project workflows')
  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  const workflows = page.locator('.v-row', {
    has: page.getByRole('heading', { name: 'Project workflows' }),
  })
  await expect(workflows.getByText('1 unsaved change')).toBeVisible()
  return workflows
}

test('an edited dialog asks before Escape discards it', async ({ page }) => {
  const messages = await recordShellMessages(page)
  await openView(page)
  await page.getByRole('button', { name: 'Create new project' }).click()
  const name = dialog(page).getByLabel('Project name')
  await name.fill('draft')
  await expect.poll(async () => lastDirty(await messages())).toBe(true)

  await pressEscapeUntil(page, () => discardQuestion(page).isVisible())
  await discardQuestion(page).getByRole('button', { name: 'Keep editing' }).click()
  await expect(discardQuestion(page)).toBeHidden()
  await expect(name).toHaveValue('draft')

  await pressEscapeUntil(page, () => discardQuestion(page).isVisible())
  await discardQuestion(page).getByRole('button', { name: 'Discard changes' }).click()
  await expect(dialog(page).filter({ visible: true })).toHaveCount(0)
  await expect.poll(async () => lastDirty(await messages())).toBe(false)
})

test('an untouched dialog closes without asking', async ({ page }) => {
  await openView(page)
  await page.getByRole('button', { name: 'Create new project' }).click()
  await dialog(page).getByRole('button', { name: 'Cancel' }).click()
  await expect(dialog(page)).toBeHidden()
})

test('Refresh asks before it drops staged changes', async ({ page }) => {
  const workflows = await stageWorkflowChange(page)

  await page.getByRole('button', { name: 'Refresh' }).click()
  await discardQuestion(page).getByRole('button', { name: 'Keep editing' }).click()
  await expect(workflows.getByText('1 unsaved change')).toBeVisible()

  await page.getByRole('button', { name: 'Refresh' }).click()
  await confirmAction(page, 'Discard changes')
  await expect(page.getByText('1 unsaved change')).toHaveCount(0)
})

test('leaving the page asks before it drops staged changes', async ({ page }) => {
  const workflows = await stageWorkflowChange(page)

  await page.getByRole('button', { name: 'Projects', exact: true }).click()
  await discardQuestion(page).getByRole('button', { name: 'Keep editing' }).click()
  await expect(workflows.getByText('1 unsaved change')).toBeVisible()
  expect(new URL(page.url()).pathname).toContain(`/project/${RESEARCH_PROJECT.id}`)

  await page.getByRole('button', { name: 'Projects', exact: true }).click()
  await confirmAction(page, 'Discard changes')
  await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
})

test('uninstalling an application keeps staged changes in the other sections', async ({ page }) => {
  const workflows = await stageWorkflowChange(page)
  await expandSection(page, 'Active project applications')

  await page.getByRole('button', { name: 'Uninstall JupyterLab (notebooks)' }).click()
  await confirmAction(page, 'Uninstall application')

  await expect(row(page, 'JupyterLab (notebooks)')).toHaveCount(0)
  await expect(workflows.getByText('1 unsaved change')).toBeVisible()
})

test('adding a right keeps staged role-right changes', async ({ page }) => {
  await openView(page)
  await page.getByRole('button', { name: 'Edit role rights' }).click()
  await row(page, 'manage_users').getByRole('checkbox').nth(2).click()
  await expect(page.getByText('1 unsaved change')).toBeVisible()

  await page.getByRole('button', { name: 'Add right' }).click()
  const form = dialog(page)
  await form.getByLabel('Name', { exact: true }).fill('export_data')
  await form.getByLabel('Description').fill('Export project data')
  await form.getByLabel('JWT claim key').fill('kaapana.ai/aii')
  await form.getByLabel('JWT claim value').fill('export_data')
  await form.getByRole('button', { name: 'Add right' }).click()

  await expect(row(page, 'export_data')).toBeVisible()
  await expect(page.getByText('1 unsaved change')).toBeVisible()
})

test('deleting a right drops only the staged changes for that right', async ({ page }) => {
  await openView(page)
  await page.getByRole('button', { name: 'Edit role rights' }).click()
  await row(page, 'manage_users').getByRole('checkbox').nth(2).click()
  await row(page, 'launch_application').getByRole('checkbox').nth(2).click()
  await expect(page.getByText('2 unsaved changes')).toBeVisible()

  await page.getByRole('button', { name: 'Delete right manage_users' }).click()
  await confirmAction(page, 'Delete right')

  await expect(row(page, 'manage_users')).toHaveCount(0)
  await expect(page.getByText('1 unsaved change')).toBeVisible()
})
