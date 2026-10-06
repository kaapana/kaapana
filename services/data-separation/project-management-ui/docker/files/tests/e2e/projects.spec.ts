import { test, expect, type Page, type Route } from '@playwright/test'
import {
  ADMIN_PROJECT,
  RESEARCH_PROJECT,
  installMockBackend,
  VIEW_PATH,
} from './fixtures/mock-backend'
import { confirmAction, openProject, openView, row } from './fixtures/helpers'

async function holdRequests(page: Page, method: string, path: RegExp) {
  let release!: () => void
  const released = new Promise<void>((resolve) => (release = resolve))
  await page.route(path, async (route: Route) => {
    if (route.request().method() !== method) return route.fallback()
    await released
    await route.fallback()
  })
  return release
}

test.describe('loading and progress', () => {
  test('the project list shows that it is loading', async ({ page }) => {
    await installMockBackend(page)
    const release = await holdRequests(page, 'GET', /\/aii\/projects$/)
    await page.goto(VIEW_PATH)

    await expect(page.getByText('Loading projects…')).toBeVisible()
    release()
    await expect(row(page, ADMIN_PROJECT.name)).toBeVisible()
  })

  test('a row action shows its progress and blocks the other actions', async ({ page }) => {
    await openView(page)
    const release = await holdRequests(page, 'POST', /\/archive$/)
    const research = row(page, RESEARCH_PROJECT.name)

    await research.getByRole('button', { name: `Archive ${RESEARCH_PROJECT.name}` }).click()
    await confirmAction(page, 'Archive project')

    const archive = research.getByRole('button', { name: `Archive ${RESEARCH_PROJECT.name}` })
    await expect(archive).toHaveClass(/v-btn--loading/)
    await expect(
      research.getByRole('button', { name: `Delete ${RESEARCH_PROJECT.name}` }),
    ).toBeDisabled()
    release()
    await expect(research.getByText('Archived')).toBeVisible()
  })

  test('a header action on the project page shows its progress', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT)
    const release = await holdRequests(
      page,
      'DELETE',
      new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}$`),
    )

    await page.getByRole('button', { name: 'Delete project' }).click()
    await confirmAction(page, 'Delete project')

    await expect(page.getByRole('button', { name: 'Delete project' })).toHaveClass(/v-btn--loading/)
    await expect(page.getByRole('button', { name: 'Edit project' })).toBeDisabled()
    release()
    await expect(page).toHaveURL(/\/projects-ui\/$/)
  })
})
