import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  defaultMockData,
  viewPathFor,
  UNSCOPED_VIEW_PATH,
  VIEW_PATH,
} from './fixtures/mock-backend'

// The /project/<short_id> document prefix IS the project selection: API calls
// must be scoped to it (not to a default or any shared state), and a document
// without the prefix adopts the user's first project by redirecting onto it.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await installMockBackend(page)
  // Deliberately NOT the first project, so a fallback-to-default would fail.
  const project = defaultMockData.projects[1]
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kaapana-backend/`),
  )
  await page.goto(viewPathFor(project))
  await page.getByRole('button', { name: /Import the data/ }).click()
  await scoped
})

test('without a project prefix the view redirects onto the first project', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(UNSCOPED_VIEW_PATH)
  await page.waitForURL(`**${VIEW_PATH}`)
  await expect(page.getByRole('button', { name: /Import the data/ })).toBeVisible()
})
