import { test, expect } from '@playwright/test'
import { RESEARCH_PROJECT, SCIENTIST_USER } from './fixtures/mock-backend'
import {
  confirmAction,
  dialog,
  dismissWithEscape,
  expandSection,
  failRoute,
  openFailureDetails,
  openProject,
  openView,
  retryFrom,
  row,
} from './fixtures/helpers'

test.describe('a list that cannot load says so instead of looking empty', () => {
  const sections = [
    {
      section: 'Project members',
      request: 'members',
      path: new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}/users$`),
      text: 'Could not load the members of this project.',
      shows: SCIENTIST_USER.email,
    },
    {
      section: 'Project members',
      request: 'member roles',
      path: /\/aii\/projects\/[^/]+\/users\/[^/]+\/roles$/,
      text: 'Could not load the members of this project.',
      shows: SCIENTIST_USER.email,
    },
    {
      section: 'Project workflows',
      request: 'workflows',
      path: /\/kaapana-backend\/client\/dags/,
      text: 'Could not load the workflows',
      shows: 'collect-metadata',
    },
    {
      section: 'Project workflows',
      request: 'whitelist',
      path: /\/aii\/projects\/[^/]+\/software-mappings$/,
      text: 'Could not load the workflows',
      shows: 'collect-metadata',
    },
    {
      section: 'Multiinstallable applications',
      request: 'extensions',
      path: /\/kube-helm-api\/extensions$/,
      text: 'Could not load the applications that can be launched.',
      shows: 'Tensorboard',
    },
    {
      section: 'Active project applications',
      request: 'active applications',
      path: /\/kube-helm-api\/active-applications$/,
      text: 'Could not load the applications running in this project.',
      shows: 'JupyterLab (notebooks)',
    },
  ]

  for (const { section, request, path, text, shows } of sections) {
    test(`${section} (${request})`, async ({ page }) => {
      await openProject(page, RESEARCH_PROJECT, undefined, {
        routes: (p) => failRoute(p, 'GET', path, 'backend unavailable', 503),
      })
      await expandSection(page, section)

      const alert = page.getByRole('alert').filter({ hasText: text })
      await expect(alert).toBeVisible()
      await alert.getByRole('button', { name: 'Details' }).click()
      await expect(dialog(page)).toContainText('503')
      await expect(dialog(page)).toContainText('backend unavailable')
      await dismissWithEscape(page)

      await retryFrom(page, alert, path)
      await expect(row(page, shows)).toBeVisible()
    })
  }

  test('role rights', async ({ page }) => {
    await openView(page, undefined, {
      routes: (p) => failRoute(p, 'GET', /\/aii\/projects\/rights$/, 'database locked'),
    })
    await page.getByRole('button', { name: 'Edit role rights' }).click()

    const alert = page
      .getByRole('alert')
      .filter({ hasText: 'Could not load the roles and rights.' })
    await expect(alert).toBeVisible()
    await expect(page.getByRole('table')).toHaveCount(0)

    await retryFrom(page, alert, /\/aii\/projects\/rights$/)
    await expect(page.getByRole('table')).toBeVisible()
  })

  test('users to add', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT, undefined, {
      routes: (p) => failRoute(p, 'GET', /\/aii\/users$/, 'Keycloak unreachable', 502),
    })
    await expandSection(page, 'Project members')
    await page.getByRole('button', { name: 'Add members' }).click()

    const alert = dialog(page)
      .getByRole('alert')
      .filter({ hasText: 'Could not load the users who can be added.' })
    await expect(alert).toBeVisible()

    await retryFrom(page, alert, /\/aii\/users$/)
    await dialog(page).getByRole('combobox', { name: 'Search and select users' }).click()
    await expect(page.getByRole('option', { name: /Alan Turing/ })).toBeVisible()
  })
})

test.describe('a failed action notifies with the backend detail behind it', () => {
  test('deleting a project', async ({ page }) => {
    await openView(page, undefined, {
      routes: (p) =>
        failRoute(p, 'DELETE', /\/aii\/projects\/[^/]+$/, 'Project has running workflows', 409),
    })
    await row(page, RESEARCH_PROJECT.name)
      .getByRole('button', { name: `Delete ${RESEARCH_PROJECT.name}` })
      .click()
    await confirmAction(page, 'Delete project')

    const details = await openFailureDetails(page, 'Project not deleted')
    await expect(details).toContainText(`Could not delete "${RESEARCH_PROJECT.name}".`)
    await expect(details).toContainText('409')
    await expect(details).toContainText('Project has running workflows')
    await page.keyboard.press('Escape')
    await expect(row(page, RESEARCH_PROJECT.name)).toBeVisible()
  })

  test('removing a member', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT, undefined, {
      routes: (p) => failRoute(p, 'DELETE', /\/rolemapping$/, 'Last principal investigator', 400),
    })
    await expandSection(page, 'Project members')
    await row(page, SCIENTIST_USER.username)
      .getByRole('button', { name: `Remove ${SCIENTIST_USER.username} from the project` })
      .click()
    await confirmAction(page, 'Remove member')

    const details = await openFailureDetails(page, 'Member not removed')
    await expect(details).toContainText('Last principal investigator')
  })

  test('adding a member keeps the dialog open with the reason', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT, undefined, {
      routes: (p) => failRoute(p, 'POST', /\/role\/[^/]+\/user\/[^/]+$/, 'User is disabled', 422),
    })
    await expandSection(page, 'Project members')
    await page.getByRole('button', { name: 'Add members' }).click()
    await dialog(page).getByRole('combobox', { name: 'Search and select users' }).click()
    await page.getByRole('option', { name: /Alan Turing/ }).click()
    await page.keyboard.press('Escape')
    await dialog(page).getByRole('button', { name: 'Add member' }).click()

    const alert = dialog(page).getByRole('alert').filter({ hasText: 'Not every selected user' })
    await expect(alert).toBeVisible()
  })
})
