import { test, expect } from '@playwright/test'
import { ADMIN_PROJECT, defaultMockData, RESEARCH_PROJECT } from './fixtures/mock-backend'
import { collectPageErrors, openProject, openView, row } from './fixtures/helpers'

test('renders the project list on a fresh profile', async ({ page }) => {
  const pageErrors = collectPageErrors(page)

  await openView(page, defaultMockData, { seedSettings: false })

  await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('opens a project from the list', async ({ page }) => {
  await openView(page)

  await row(page, RESEARCH_PROJECT.name).getByRole('button', { name: 'View' }).click()

  await expect(page).toHaveURL(new RegExp(`/projects-ui/project/${RESEARCH_PROJECT.id}$`))
  await expect(page.getByText(RESEARCH_PROJECT.description!)).toBeVisible()
})

test('renders a project detail page directly', async ({ page }) => {
  const pageErrors = collectPageErrors(page)

  await openProject(page, ADMIN_PROJECT)

  await expect(page.getByText('Project Users')).toBeVisible()
  expect(pageErrors).toEqual([])
})
