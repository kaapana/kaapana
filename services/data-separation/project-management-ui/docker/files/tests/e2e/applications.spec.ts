import { test, expect, type Page } from '@playwright/test'
import { defaultMockData, RESEARCH_PROJECT, type MockData } from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  dialog,
  expandSection,
  failRoute,
  nextRequest,
  openProject,
  row,
} from './fixtures/helpers'

async function open(page: Page, data: MockData = defaultMockData) {
  const state = await openProject(page, RESEARCH_PROJECT, data)
  await expandSection(page, 'Multiinstallable applications')
  await expandSection(page, 'Active project applications')
  return state
}

const appsSection = (page: Page) =>
  page.locator('.v-row', {
    has: page.getByRole('heading', { name: 'Multiinstallable applications' }),
  })

test('launches an application with its parameters and lists the new instance', async ({ page }) => {
  await open(page)
  await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()
  const form = dialog(page)
  await expect(form.getByText('Configure JupyterLab')).toBeVisible()
  await expect(form.getByRole('button', { name: 'Field help' })).toBeVisible()
  await form.getByRole('textbox', { name: 'Workspace name (workspace_name)' }).fill('cohort-a')

  const request = nextRequest(page, 'POST', '/kube-helm-api/helm-install-chart')
  await form.getByRole('button', { name: 'Launch' }).click()
  const sent = await request
  expect(new URL(sent.url()).pathname).toBe(
    `/project/${RESEARCH_PROJECT.short_id}/kube-helm-api/helm-install-chart`,
  )
  expect(sent.postDataJSON()).toEqual({
    name: 'jupyterlab',
    version: '4.2.0',
    keywords: ['kaapana-application'],
    extension_params: { workspace_name: 'cohort-a' },
  })

  await expect(form).toBeHidden()
  await expect(row(page, 'jupyterlab (launched)')).toBeVisible()
})

test('launches an application without parameters directly', async ({ page }) => {
  await open(page)

  const request = nextRequest(page, 'POST', '/kube-helm-api/helm-install-chart')
  await row(page, 'Tensorboard').getByRole('button', { name: 'Launch' }).click()
  const sent = await request
  expect(sent.postDataJSON()).toEqual({
    name: 'tensorboard',
    version: '2.17.0',
    keywords: ['kaapana-application'],
    extension_params: {},
  })

  await expect(page.getByText('Tensorboard is starting.')).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('keeps the launch form with its values when the launch fails', async ({ page }) => {
  await openProject(page, RESEARCH_PROJECT, undefined, {
    routes: (p) => failRoute(p, 'POST', /\/helm-install-chart$/, 'quota exceeded'),
  })
  await expandSection(page, 'Multiinstallable applications')
  await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()
  const form = dialog(page)
  const name = form.getByRole('textbox', { name: 'Workspace name (workspace_name)' })
  await name.fill('cohort-a')
  await form.getByRole('button', { name: 'Launch' }).click()

  await expect(page.getByText('Application not launched')).toBeVisible()
  await expect(form).toBeVisible()
  await expect(name).toHaveValue('cohort-a')
})

test('validates the launch form and sends nothing while it is invalid', async ({ page }) => {
  await open(page)
  const sent: string[] = []
  page.on('request', (r) => r.method() === 'POST' && sent.push(r.url()))
  await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()
  const form = dialog(page)
  await form.getByRole('textbox', { name: 'Workspace name (workspace_name)' }).clear()

  await form.getByRole('button', { name: 'Launch' }).click()

  await expect(form.getByText('Enter a value.')).toBeVisible()
  await expect(form).toBeVisible()
  expect(sent).toEqual([])
})

test('renders applications without a description or documentation', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  const bare = {
    ...defaultMockData.extensions[1],
    description: undefined,
    annotations: { 'ui-visible-name': 'Bare' },
  }
  await open(page, { ...defaultMockData, extensions: [bare] })

  await expect(row(page, 'Bare')).toBeVisible()
  await expect(row(page, 'Bare').getByRole('link')).toHaveCount(0)
  expect(pageErrors).toEqual([])
})

test('uninstalls an application', async ({ page }) => {
  await open(page)

  await page.getByRole('button', { name: 'Uninstall JupyterLab (notebooks)' }).click()
  await confirmAction(page, 'Uninstall application')

  // helm uninstall runs in the background; the request only starts it.
  await expect(page.getByText('JupyterLab (notebooks) is being removed.')).toBeVisible()
  await expect(row(page, 'JupyterLab (notebooks)')).toHaveCount(0)
})

test('sorts running applications by the name they show', async ({ page }) => {
  const second = {
    ...defaultMockData.activeApplications[0],
    release_name: 'tensorboard-x1',
    annotations: { 'kaapana.ai/display-name': 'Alpha board' },
  }
  await open(page, {
    ...defaultMockData,
    activeApplications: [...defaultMockData.activeApplications, second],
  })
  const active = page.locator('.v-row', {
    has: page.getByRole('heading', { name: 'Active project applications' }),
  })
  const names = active.locator('tbody tr td:nth-child(2)')

  await expect(names).toHaveText(['Alpha board', 'JupyterLab (notebooks)'])
  await active.getByRole('columnheader', { name: /Name/ }).click()
  await expect(names).toHaveText(['JupyterLab (notebooks)', 'Alpha board'])
})

test('saves the application whitelist without dropping existing entries', async ({ page }) => {
  const state = await open(page, {
    ...defaultMockData,
    whitelists: { [RESEARCH_PROJECT.id]: ['jupyterlab'] },
  })

  await expect(row(page, 'JupyterLab').getByRole('checkbox')).toBeChecked()
  await row(page, 'Tensorboard').getByRole('checkbox').click()
  await appsSection(page).getByRole('button', { name: 'Save changes' }).click()

  await expect(appsSection(page).getByText('unsaved')).toHaveCount(0)
  expect(state.whitelists[RESEARCH_PROJECT.id]).toEqual(['jupyterlab', 'tensorboard'])
})

test('does not offer the whitelist when it could not be loaded', async ({ page }) => {
  await openProject(page, RESEARCH_PROJECT, undefined, {
    routes: (p) => failRoute(p, 'GET', /\/multiinstallable-whitelist$/, 'database locked'),
  })
  await expandSection(page, 'Multiinstallable applications')

  await expect(
    appsSection(page).getByRole('alert').filter({ hasText: 'Could not load the applications' }),
  ).toBeVisible()
  await expect(row(page, 'Tensorboard')).toHaveCount(0)
})
