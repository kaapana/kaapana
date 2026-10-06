import { test, expect, type Page } from '@playwright/test'
import { ADMIN_PROJECT, RESEARCH_PROJECT } from './fixtures/mock-backend'
import { confirmAction, expandSection, openProject, openView, row } from './fixtures/helpers'

// On a project page the scoped backends get its /project/<short_id>/ prefix, so
// the gateway authorises against that project. AII is never prefixed.

const LEGACY = /(^|\/)(kaapana-backend|kube-helm-api)\//

function recordPaths(page: Page) {
  const paths: string[] = []
  page.on('request', (r) => {
    const path = new URL(r.url()).pathname
    if (LEGACY.test(path) || path.includes('/aii/')) paths.push(path)
  })
  return paths
}

test('project-scoped calls carry the prefix of the project on screen', async ({ page }) => {
  const paths = recordPaths(page)
  await openProject(page, RESEARCH_PROJECT)
  await expandSection(page, 'Project workflows')
  await expandSection(page, 'Multiinstallable applications')
  await expandSection(page, 'Active project applications')

  await row(page, 'Tensorboard').getByRole('button', { name: 'Launch' }).click()
  await expect(page.getByText('Tensorboard is starting.')).toBeVisible()
  await page.getByRole('button', { name: 'Uninstall JupyterLab (notebooks)' }).click()
  await confirmAction(page, 'Uninstall application')
  await expect(row(page, 'JupyterLab (notebooks)')).toHaveCount(0)

  const legacy = paths.filter((p) => LEGACY.test(p) && !p.endsWith('/open-policy-data'))
  expect(legacy.length).toBeGreaterThan(0)
  for (const path of legacy) {
    expect(path, 'unscoped or wrongly scoped call').toMatch(
      new RegExp(`^/project/${RESEARCH_PROJECT.short_id}/(kaapana-backend|kube-helm-api)/`),
    )
  }
  for (const path of paths.filter((p) => p.includes('/aii/'))) {
    expect(path).toMatch(/^\/aii\//)
  }
})

test('the policy data is read unscoped', async ({ page }) => {
  const policy = page.waitForRequest((r) => r.url().endsWith('/open-policy-data'))
  await openProject(page, RESEARCH_PROJECT)

  expect(new URL((await policy).url()).pathname).toBe('/kaapana-backend/open-policy-data')
})

test('opening another project switches the prefix with it', async ({ page }) => {
  await openView(page)
  await row(page, RESEARCH_PROJECT.name).getByRole('button', { name: 'View' }).click()
  await page.getByRole('button', { name: 'Projects', exact: true }).click()

  const paths = recordPaths(page)
  await row(page, ADMIN_PROJECT.name).getByRole('button', { name: 'View' }).click()
  await expandSection(page, 'Project workflows')
  await expect(row(page, 'collect-metadata')).toBeVisible()

  const legacy = paths.filter((p) => LEGACY.test(p))
  expect(legacy.length).toBeGreaterThan(0)
  for (const path of legacy) expect(path).toMatch(/^\/project\/admin\//)
})
