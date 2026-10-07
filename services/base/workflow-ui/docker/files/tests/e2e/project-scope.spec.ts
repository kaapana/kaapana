import { test, expect } from '@playwright/test'
import { openRunForm, openRuns, openWorkflows } from './fixtures/helpers'
import { PROJECT } from './fixtures/mock-backend'

// The shell serves the view under /project/<short_id>/; every call to a
// project-scoped backend must carry that prefix, or the gateway cannot inject
// the Project header and the backend answers 400.
test.describe('project scope', () => {
  test('workflow-api and kaapana-backend calls carry the project prefix', async ({ page }) => {
    const urls: string[] = []
    page.on('request', (r) => {
      if (/\/(workflow-api|kaapana-backend)\//.test(r.url())) urls.push(new URL(r.url()).pathname)
    })
    await openWorkflows(page)
    await openRunForm(page, 'Segmentation')
    await openRuns(page)

    expect(urls.length).toBeGreaterThan(0)
    for (const url of urls)
      expect(url).toMatch(new RegExp(`^/project/${PROJECT}/(workflow-api|kaapana-backend)/`))
    expect(urls).toContain(`/project/${PROJECT}/kaapana-backend/client/datasets`)
  })

  test('the router resolves its routes under the project prefix', async ({ page }) => {
    await openRuns(page)
    await expect(page).toHaveURL(new RegExp(`/project/${PROJECT}/workflow-ui/runs$`))
  })
})
