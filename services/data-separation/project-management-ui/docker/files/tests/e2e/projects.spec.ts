import { test, expect, type Page, type Route } from '@playwright/test'
import type { UserItem } from '@/common/types'
import {
  ADMIN_PROJECT,
  ADMIN_USER,
  defaultMockData,
  installMockBackend,
  RESEARCH_PROJECT,
  SCIENTIST_USER,
  VIEW_PATH,
} from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  failRoute,
  openProject,
  openView,
  retryFrom,
  row,
} from './fixtures/helpers'

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

test.describe('project list', () => {
  const ADMIN_IN_NO_PROJECT: UserItem = {
    ...ADMIN_USER,
    id: '00000000-0000-0000-0000-000000000020',
    username: 'root',
    realm_roles: ['admin', 'user'],
  }

  test('an admin sees every project, also without the project-manager role', async ({ page }) => {
    await openView(page, { ...defaultMockData, currentUser: ADMIN_IN_NO_PROJECT })

    await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
    await expect(row(page, ADMIN_PROJECT.name)).toBeVisible()
  })

  test('a user sees the projects they are a member of', async ({ page }) => {
    await installMockBackend(page, { ...defaultMockData, currentUser: SCIENTIST_USER })
    await page.goto(VIEW_PATH)

    await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
    await expect(row(page, ADMIN_PROJECT.name)).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Create New Project' })).toHaveCount(0)
  })

  test('a list that cannot load says so', async ({ page }) => {
    const pageErrors = collectPageErrors(page)
    await installMockBackend(page)
    await failRoute(page, 'GET', /\/aii\/projects$/, 'database locked')
    await page.goto(VIEW_PATH)

    const alert = page.getByRole('alert').filter({ hasText: 'Could not load the projects.' })
    await expect(alert).toBeVisible()

    await retryFrom(page, alert, /\/aii\/projects$/)
    await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
    expect(pageErrors).toEqual([])
  })
})
