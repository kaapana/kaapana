import { test, expect, type Page, type Route } from '@playwright/test'
import type { UserItem } from '@/common/types'
import {
  ADMIN_PROJECT,
  ADMIN_USER,
  CANDIDATE_USER,
  defaultMockData,
  installMockBackend,
  RESEARCH_PROJECT,
  projectPath,
  SCIENTIST_USER,
  VIEW_PATH,
} from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  dialog,
  discardQuestion,
  failRoute,
  nextRequest,
  openProject,
  openView,
  retryFrom,
  row,
  toasts,
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

  test('shows every project on one page', async ({ page }) => {
    const studies = Array.from({ length: 12 }, (_, i) => ({
      ...RESEARCH_PROJECT,
      id: `5e7a9c1b-0000-0000-0000-${String(i).padStart(12, '0')}`,
      short_id: `study${i}`,
      name: `study-${i}`,
    }))
    const projects = [ADMIN_PROJECT, ...studies]
    await openView(page, { ...defaultMockData, projects })

    await expect(page.locator('tbody tr')).toHaveCount(projects.length)
  })

  test('a search that matches nothing says so and can be cleared', async ({ page }) => {
    await openView(page)
    await page.getByRole('textbox', { name: 'Search projects' }).fill('liver')

    await expect(page.getByText('No projects match "liver"')).toBeVisible()
    await page.getByRole('button', { name: 'Clear search', exact: true }).click()
    await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
  })

  test('a user in no project learns how to join one', async ({ page }) => {
    await installMockBackend(page, { ...defaultMockData, currentUser: CANDIDATE_USER })
    await page.goto(VIEW_PATH)

    await expect(page.getByText('You are not in any project yet')).toBeVisible()
    await expect(
      page.getByText("Ask a project manager or a project's principal investigator to add you."),
    ).toBeVisible()
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

test.describe('creating a project', () => {
  test('creates the project and lists it', async ({ page }) => {
    const state = await openView(page)
    await page.getByRole('button', { name: 'Create New Project' }).click()
    const form = dialog(page)
    await form.getByLabel('Project name').fill('liver-ct')
    await form.getByLabel('Description').fill('Liver CT cohort')
    await form.getByLabel('External ID (optional)').fill('EXT-7')

    const request = nextRequest(page, 'POST', '/aii/projects')
    await form.getByRole('button', { name: 'Create project' }).click()
    expect((await request).postDataJSON()).toEqual({
      name: 'liver-ct',
      description: 'Liver CT cohort',
      external_id: 'EXT-7',
    })

    await expect(form).toBeHidden()
    await expect(row(page, 'liver-ct')).toBeVisible()
    expect(state.projects.map((p) => p.name)).toContain('liver-ct')
  })

  test('validates on submit and sends nothing while the form is invalid', async ({ page }) => {
    await openView(page)
    const sent: string[] = []
    page.on('request', (r) => r.method() === 'POST' && sent.push(r.url()))
    await page.getByRole('button', { name: 'Create New Project' }).click()
    const form = dialog(page)
    await form.getByLabel('Project name').fill('Liver CT')

    await form.getByRole('button', { name: 'Create project' }).click()

    await expect(form.getByText('Use lowercase; capital letters are not allowed.')).toBeVisible()
    await expect(form.getByText('Enter a description.')).toBeVisible()
    await form.getByLabel('Project name').fill('liver_ct')
    await expect(form.getByText('Use only lowercase letters, digits and hyphens.')).toBeVisible()
    expect(sent).toEqual([])
  })

  test('keeps the dialog open with the reason when the backend refuses', async ({ page }) => {
    await openView(page, undefined, {
      routes: (p) => failRoute(p, 'POST', /\/aii\/projects$/, 'Name already taken', 409),
    })
    await page.getByRole('button', { name: 'Create New Project' }).click()
    const form = dialog(page)
    await form.getByLabel('Project name').fill('lung-study')
    await form.getByLabel('Description').fill('Duplicate')
    await form.getByRole('button', { name: 'Create project' }).click()

    const alert = form.getByRole('alert').filter({ hasText: 'The project could not be created.' })
    await expect(alert).toBeVisible()
    await alert.getByRole('button', { name: 'Details' }).click()
    await expect(page.getByText('Name already taken')).toBeVisible()
  })

  test('starts empty every time it opens', async ({ page }) => {
    await openView(page)
    await page.getByRole('button', { name: 'Create New Project' }).click()
    await dialog(page).getByLabel('Project name').fill('draft')
    await dialog(page).getByRole('button', { name: 'Cancel' }).click()
    await discardQuestion(page).getByRole('button', { name: 'Discard changes' }).click()
    await expect(dialog(page).filter({ visible: true })).toHaveCount(0)

    await page.getByRole('button', { name: 'Create New Project' }).click()
    await expect(dialog(page).getByLabel('Project name')).toHaveValue('')
  })
})

test.describe('editing, archiving and deleting', () => {
  test('saves an edit and shows it in the list', async ({ page }) => {
    await openView(page)
    await row(page, RESEARCH_PROJECT.name)
      .getByRole('button', { name: `Edit ${RESEARCH_PROJECT.name}` })
      .click()
    await dialog(page).getByLabel('Description').fill('Lung nodule follow-up')
    await dialog(page).getByRole('button', { name: 'Save' }).click()

    await expect(dialog(page)).toBeHidden()
    await expect(row(page, RESEARCH_PROJECT.name)).toContainText('Lung nodule follow-up')
  })

  test('an edit checks the name only when it changes', async ({ page }) => {
    const legacy = { ...RESEARCH_PROJECT, name: 'Lung_Study' }
    await openView(page, { ...defaultMockData, projects: [ADMIN_PROJECT, legacy] })
    await row(page, legacy.name)
      .getByRole('button', { name: `Edit ${legacy.name}` })
      .click()
    const form = dialog(page)

    await form.getByLabel('Description').fill('')
    await form.getByRole('button', { name: 'Save' }).click()
    await expect(form.getByText('Enter a description.')).toBeVisible()

    await form.getByLabel('Description').fill('Lung nodule follow-up')
    await form.getByRole('button', { name: 'Save' }).click()
    await expect(form).toBeHidden()

    await row(page, legacy.name)
      .getByRole('button', { name: `Edit ${legacy.name}` })
      .click()
    await form.getByLabel('Project name').fill('Lung_Study2')
    await form.getByRole('button', { name: 'Save' }).click()
    await expect(form.getByText('Use lowercase; capital letters are not allowed.')).toBeVisible()
  })

  test('a cancelled edit leaves nothing behind for the next one', async ({ page }) => {
    await openView(page)
    const edit = row(page, RESEARCH_PROJECT.name).getByRole('button', {
      name: `Edit ${RESEARCH_PROJECT.name}`,
    })
    await edit.click()
    await dialog(page).getByLabel('Description').fill('discarded')
    await dialog(page).getByRole('button', { name: 'Cancel' }).click()
    await discardQuestion(page).getByRole('button', { name: 'Discard changes' }).click()
    await expect(dialog(page).filter({ visible: true })).toHaveCount(0)

    await edit.click()
    await expect(dialog(page).getByLabel('Description')).toHaveValue(RESEARCH_PROJECT.description!)
  })

  test('keeps the edit open with the reason when the backend refuses', async ({ page }) => {
    await openView(page, undefined, {
      routes: (p) =>
        failRoute(p, 'PUT', new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}$`), 'database locked'),
    })
    await row(page, RESEARCH_PROJECT.name)
      .getByRole('button', { name: `Edit ${RESEARCH_PROJECT.name}` })
      .click()
    await dialog(page).getByLabel('Description').fill('Lung nodule follow-up')
    await dialog(page).getByRole('button', { name: 'Save' }).click()

    const alert = dialog(page)
      .getByRole('alert')
      .filter({ hasText: `Could not save "${RESEARCH_PROJECT.name}".` })
    await expect(alert).toBeVisible()
    await expect(dialog(page).getByLabel('Description')).toHaveValue('Lung nodule follow-up')
    await alert.getByRole('button', { name: 'Details' }).click()
    await expect(page.getByText('database locked')).toBeVisible()
  })

  test('archives, unarchives and deletes a project', async ({ page }) => {
    await openView(page)
    const research = row(page, RESEARCH_PROJECT.name)

    await research.getByRole('button', { name: `Archive ${RESEARCH_PROJECT.name}` }).click()
    await confirmAction(page, 'Archive project')
    await expect(research.getByText('Archived')).toBeVisible()

    await research.getByRole('button', { name: `Unarchive ${RESEARCH_PROJECT.name}` }).click()
    await expect(research.getByText('Archived')).toHaveCount(0)

    await research.getByRole('button', { name: `Delete ${RESEARCH_PROJECT.name}` }).click()
    await confirmAction(page, 'Delete project')
    await expect(research).toHaveCount(0)
  })

  test('the admin project cannot be changed', async ({ page }) => {
    await openView(page)

    await expect(row(page, ADMIN_PROJECT.name).getByRole('button')).toHaveText(['View'])
  })
})

test.describe('project page', () => {
  test('opens without announcing itself', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT)

    await expect(page.getByText(RESEARCH_PROJECT.description!)).toBeVisible()
    await expect(toasts(page)).toHaveCount(0)
  })

  test('says so when the project cannot be loaded', async ({ page }) => {
    await installMockBackend(page)
    await failRoute(
      page,
      'GET',
      new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}$`),
      'Not found',
      404,
    )
    await page.goto(projectPath(RESEARCH_PROJECT))

    const alert = page.getByRole('alert').filter({ hasText: 'Could not load this project.' })
    await expect(alert).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Project Users' })).toHaveCount(0)

    await retryFrom(page, alert, new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}$`))
    await expect(page.getByRole('heading', { name: 'Project Users' })).toBeVisible()
  })

  test('an edit updates the header', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT)
    await page.getByRole('button', { name: 'Edit project' }).click()
    await dialog(page).getByLabel('External ID (optional)').fill('EXT-99')
    await dialog(page).getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('EXT-99')).toBeVisible()
  })

  test('a deletion returns to the list and says so', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT)
    await page.getByRole('button', { name: 'Delete project' }).click()
    await confirmAction(page, 'Delete project')

    await expect(page).toHaveURL(/\/projects-ui\/$/)
    await expect(toasts(page)).toContainText(`Project "${RESEARCH_PROJECT.name}" deleted.`)
    await expect(row(page, RESEARCH_PROJECT.name)).toHaveCount(0)
  })
})
