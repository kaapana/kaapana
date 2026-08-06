import { test, expect } from '@playwright/test'
import {
  bootGallery,
  makeDefaultMockData,
  viewPathFor,
  UNSCOPED_VIEW_PATH,
  VIEW_PATH,
} from './fixtures/mock-backend'

// The /project/<short_id> document prefix IS the project selection: API calls
// must be scoped to it (not to a default or any shared state), and a document
// without the prefix adopts the user's first project by redirecting onto it.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  const data = makeDefaultMockData()
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const project = data.projects[1]
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kaapana-backend/`),
  )
  await bootGallery(page, data, viewPathFor(project))
  await scoped
})

test('without a project prefix the view redirects onto the first project', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData(), UNSCOPED_VIEW_PATH)
  await page.waitForURL(`**${VIEW_PATH}`)
  await expect(page.getByText('CT Thorax')).toBeVisible()
})

test('?project_name deep link to another project moves the document under its prefix', async ({ page }) => {
  const data = makeDefaultMockData()
  const target = data.projects[1]
  await bootGallery(page, data, `${VIEW_PATH}?project_name=${target.name}`)
  await page.waitForURL(`**${viewPathFor(target)}?project_name=${target.name}`)
})
