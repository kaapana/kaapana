import { test } from '@playwright/test'
import { installMockBackend, seedShellState, viewPathFor } from './fixtures/mock-backend'

// The /project/<short_id> document prefix IS the project selection: API calls
// must be scoped to it (not to a default or any shared state). This view keeps
// no project store, so served without the prefix it simply sends unscoped API
// calls — there is no redirect-onto-first-project behavior to test here.

test('API calls are scoped to the project in the document URL', async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Deliberately NOT the project VIEW_PATH scopes to, so a fallback to any
  // default would fail. The view never fetches a project list, so the slug
  // only has to appear in the document URL.
  const project = { short_id: 'resb' }
  const scoped = page.waitForRequest((r) =>
    r.url().includes(`/project/${project.short_id}/kaapana-backend/`),
  )
  await page.goto(viewPathFor(project))
  await scoped
})
