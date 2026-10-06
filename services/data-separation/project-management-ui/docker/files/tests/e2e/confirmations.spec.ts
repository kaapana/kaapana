import { test, expect, type Page } from '@playwright/test'
import { RESEARCH_PROJECT, SCIENTIST_USER } from './fixtures/mock-backend'
import {
  confirmAction,
  dialog,
  expandSection,
  openProject,
  openView,
  row,
} from './fixtures/helpers'

interface Case {
  name: string
  open: (page: Page) => Promise<unknown>
  trigger: (page: Page) => Promise<unknown>
  confirmText: string
  method: string
  url: RegExp
}

const projectList = (page: Page) => openView(page)
const projectPage = (page: Page) => openProject(page, RESEARCH_PROJECT)
const rightsPage = async (page: Page) => {
  await openView(page)
  await page.getByRole('button', { name: 'Edit Role Rights' }).click()
  await expect(page.getByText('manage_users', { exact: true })).toBeVisible()
}

const cases: Case[] = [
  {
    name: 'delete a project from the list',
    open: projectList,
    trigger: (page) =>
      row(page, RESEARCH_PROJECT.name)
        .getByRole('button', { name: `Delete ${RESEARCH_PROJECT.name}` })
        .click(),
    confirmText: 'Delete project',
    method: 'DELETE',
    url: new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}$`),
  },
  {
    name: 'archive a project from its page',
    open: projectPage,
    trigger: (page) => page.getByRole('button', { name: 'Archive project' }).click(),
    confirmText: 'Archive project',
    method: 'POST',
    url: new RegExp(`/aii/projects/${RESEARCH_PROJECT.id}/archive$`),
  },
  {
    name: 'remove a member',
    open: async (page) => {
      await projectPage(page)
      await expandSection(page, 'Project Users')
    },
    trigger: (page) =>
      row(page, SCIENTIST_USER.username)
        .getByRole('button', { name: `Remove ${SCIENTIST_USER.username} from the project` })
        .click(),
    confirmText: 'Remove user',
    method: 'DELETE',
    url: new RegExp(`/user/${SCIENTIST_USER.id}/rolemapping$`),
  },
  {
    name: 'uninstall an application',
    open: async (page) => {
      await projectPage(page)
      await expandSection(page, 'Active Project Applications')
    },
    trigger: (page) =>
      page.getByRole('button', { name: 'Uninstall JupyterLab (notebooks)' }).click(),
    confirmText: 'Uninstall application',
    method: 'POST',
    url: /\/kube-helm-api\/helm-delete-chart$/,
  },
  {
    name: 'delete a right',
    open: rightsPage,
    trigger: (page) => page.getByRole('button', { name: 'Delete right manage_users' }).click(),
    confirmText: 'Delete right',
    method: 'DELETE',
    url: /\/aii\/projects\/rights\/1$/,
  },
  {
    name: 'reset role rights',
    open: rightsPage,
    trigger: (page) => page.getByRole('button', { name: 'Reset to Defaults' }).click(),
    confirmText: 'Reset to defaults',
    method: 'POST',
    url: /\/aii\/projects\/rights\/reset$/,
  },
]

for (const c of cases) {
  test(`asks before it ${c.name}`, async ({ page }) => {
    await c.open(page)
    const sent: string[] = []
    page.on('request', (r) => {
      if (r.method() === c.method && c.url.test(new URL(r.url()).pathname)) sent.push(r.url())
    })

    await c.trigger(page)
    await dialog(page).getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog(page)).toBeHidden()
    expect(sent).toEqual([])

    await c.trigger(page)
    await confirmAction(page, c.confirmText)
    await expect.poll(() => sent.length).toBe(1)
  })
}
