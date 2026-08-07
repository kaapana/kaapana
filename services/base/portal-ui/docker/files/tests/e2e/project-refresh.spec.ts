import { test, expect, type Page } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'
import type { Project } from '../../src/api/projects'

const ADMIN: Project = { id: 1, name: 'admin', short_id: 'admin' }
const RESB: Project = { id: 2, name: 'research-b', short_id: 'resb' }
const NEWP: Project = { id: 3, name: 'new-study', short_id: 'newp' }

// Serve /aii/projects from a mutable list so a later poll can return a different
// set. Must be routed AFTER installMockBackend so this override wins.
async function routeProjects(page: Page, get: () => Project[]) {
  await page.route('**/aii/projects', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(get()) }),
  )
}

test('a later poll picks up a newly created project in the selector', async ({ page }) => {
  await page.clock.install()
  let projects: Project[] = [ADMIN, RESB]
  await installMockBackend(page)
  await routeProjects(page, () => projects)
  await stubView(page, '/data-gallery-ui')

  await page.goto('/')
  await expect(page).toHaveURL(/\/project\/admin/)

  // A new project appears on the backend; the 15s poll must surface it.
  projects = [ADMIN, RESB, NEWP]
  await page.clock.runFor(15_000)

  await page.locator('.project-select .v-field__input').click()
  await expect(page.getByRole('option', { name: /new-study/ })).toBeVisible()
  // The selection is untouched by the refresh.
  await expect(page).toHaveURL(/\/project\/admin/)
})

test('the selected project being removed falls back to a still-available one', async ({ page }) => {
  await page.clock.install()
  let projects: Project[] = [ADMIN, RESB]
  await installMockBackend(page)
  await routeProjects(page, () => projects)
  await stubView(page, '/data-gallery-ui')

  await page.goto('/')
  await expect(page).toHaveURL(/\/project\/admin/)

  // admin (the selection) is deleted; the poll must re-target onto a remaining
  // project like the router's unknown-project branch.
  projects = [RESB]
  await page.clock.runFor(15_000)

  await expect(page).toHaveURL(/\/project\/resb/)
})

test('a project appearing while none is selected can be picked from the unscoped shell', async ({
  page,
}) => {
  // Boot with no projects: the shell stays unscoped at "/". A project then
  // appears on a poll; selecting it must prefix "/project/<slug>" (regression:
  // switchTo used to leave "/" and push a no-op when there was no prefix).
  await page.clock.install()
  let projects: Project[] = []
  await installMockBackend(page, { ...defaultMockData, projects: [] })
  await routeProjects(page, () => projects)
  await stubView(page, '/data-gallery-ui')

  await page.goto('/')
  await expect(page).toHaveURL(/localhost:\d+\/$/)

  projects = [ADMIN]
  await page.clock.runFor(15_000)

  await page.locator('.project-select .v-field__input').click()
  await page.getByRole('option', { name: /admin/ }).click()
  await expect(page).toHaveURL(/\/project\/admin/)
})
