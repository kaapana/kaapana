import { test, expect } from '@playwright/test'
import { defaultMockData, RESEARCH_PROJECT, type MockData } from './fixtures/mock-backend'
import { expandSection, openProject, row, serverError } from './fixtures/helpers'

async function open(page: import('@playwright/test').Page, data: MockData = defaultMockData) {
  const state = await openProject(page, RESEARCH_PROJECT, data)
  await expandSection(page, 'Project workflows')
  return state
}

const section = (page: import('@playwright/test').Page) =>
  page.locator('.v-row', { has: page.getByRole('heading', { name: 'Project workflows' }) })

test('shows which workflows the project may run', async ({ page }) => {
  await open(page)

  await expect(row(page, 'collect-metadata').getByRole('checkbox')).toBeChecked()
  await expect(row(page, 'nnunet-predict').getByRole('checkbox')).not.toBeChecked()
})

test('stages changes and saves them to the whitelist', async ({ page }) => {
  const state = await open(page)

  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  await row(page, 'collect-metadata').getByRole('checkbox').click()
  await expect(section(page).getByText('2 unsaved changes')).toBeVisible()
  await section(page).getByRole('button', { name: 'Save changes' }).click()

  await expect(section(page).getByText('unsaved')).toHaveCount(0)
  expect(state.softwareMappings[RESEARCH_PROJECT.id]).toEqual(['nnunet-predict'])
})

test('a partly failed save keeps the changes that failed', async ({ page }) => {
  const state = await open(page)
  let deleteFailed = false
  await page.route(/\/software-mappings$/, (r) => {
    if (r.request().method() !== 'DELETE' || deleteFailed) return r.fallback()
    deleteFailed = true
    return r.fulfill(serverError('backend unavailable', 503))
  })

  await row(page, 'nnunet-predict').getByRole('checkbox').click()
  await row(page, 'collect-metadata').getByRole('checkbox').click()
  await section(page).getByRole('button', { name: 'Save changes' }).click()

  await expect(page.getByText('Workflows partly saved')).toBeVisible()
  await expect(section(page).getByText('1 unsaved change')).toBeVisible()
  await expect(row(page, 'collect-metadata').getByRole('checkbox')).not.toBeChecked()
  expect(state.softwareMappings[RESEARCH_PROJECT.id]).toContain('nnunet-predict')

  const sent: string[] = []
  page.on('request', (r) => r.url().endsWith('/software-mappings') && sent.push(r.method()))
  await section(page).getByRole('button', { name: 'Save changes' }).click()

  await expect(section(page).getByText('unsaved')).toHaveCount(0)
  expect(state.softwareMappings[RESEARCH_PROJECT.id]).toEqual(['nnunet-predict'])
  expect(sent).toEqual(['DELETE'])
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

  await section(page).getByRole('button', { name: 'Save changes' }).click()
  await expect(cell).not.toHaveClass(/pm-pending/)
})
