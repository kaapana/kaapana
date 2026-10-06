import { test, expect } from '@playwright/test'
import { defaultMockData, RESEARCH_PROJECT, type MockData } from './fixtures/mock-backend'
import { expandSection, openProject, row } from './fixtures/helpers'

async function open(page: import('@playwright/test').Page, data: MockData = defaultMockData) {
  const state = await openProject(page, RESEARCH_PROJECT, data)
  await expandSection(page, 'Project Workflows')
  return state
}

const section = (page: import('@playwright/test').Page) =>
  page.locator('.v-row', { has: page.getByRole('heading', { name: 'Project Workflows' }) })

test('shows which workflows the project may run', async ({ page }) => {
  await open(page)

  await expect(row(page, 'collect-metadata').getByRole('checkbox')).toBeChecked()
  await expect(row(page, 'nnunet-predict').getByRole('checkbox')).not.toBeChecked()
})

test('stages changes and saves them to the whitelist', async ({ page }) => {
  const state = await open(page)

  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  await row(page, 'collect-metadata').getByRole('checkbox').click()
  await expect(section(page).getByText('2 unsaved')).toBeVisible()
  await section(page).getByRole('button', { name: 'Save Changes' }).click()

  await expect(section(page).getByText('unsaved')).toHaveCount(0)
  expect(state.softwareMappings[RESEARCH_PROJECT.id]).toEqual(['nnunet-predict'])
})

test('discards staged changes', async ({ page }) => {
  await open(page)

  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  await section(page).getByRole('button', { name: 'Discard' }).click()

  await expect(row(page, 'nnunet-predict').getByRole('checkbox')).not.toBeChecked()
  await expect(section(page).getByText('unsaved')).toHaveCount(0)
})

test('the whitelist of an archived project cannot be changed', async ({ page }) => {
  await open(page, {
    ...defaultMockData,
    projects: [defaultMockData.projects[0], { ...RESEARCH_PROJECT, is_archived: true }],
  })

  await expect(row(page, 'nnunet-predict').getByRole('checkbox')).toBeDisabled()
})

test('a staged change is marked until it is saved', async ({ page }) => {
  await open(page)
  const cell = row(page, 'nnunet-predict').getByRole('cell').last()

  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  await expect(cell).toHaveClass(/pm-pending/)
  await expect(cell).not.toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')

  await section(page).getByRole('button', { name: 'Save Changes' }).click()
  await expect(cell).not.toHaveClass(/pm-pending/)
})
