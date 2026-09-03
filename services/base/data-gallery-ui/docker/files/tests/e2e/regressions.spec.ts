// Pins Vuetify 2→3 migration regressions reported from platform QA.
import { test, expect } from '@playwright/test'
import {
  bootGallery,
  installMockBackend,
  seedShellState,
  makeDefaultMockData,
  VIEW_PATH,
} from './fixtures/mock-backend'

// query_values returns {text, value, count} objects; v3 autocompletes need
// item-title="text" or every entry renders as "[object Object]".
test('filter value dropdown shows readable labels, not [object Object]', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.locator('.mdi-filter-plus-outline').click()
  // pick the Modality key (index 0 is the Select Dataset autocomplete)
  await page.locator('.v-autocomplete input').nth(1).click()
  await page.getByRole('option', { name: 'Modality', exact: true }).click()
  await page.locator('.v-autocomplete input').nth(2).click()
  await expect(page.getByRole('option', { name: /CT\s+\(2\)/ })).toBeVisible()
  await expect(page.getByText('[object Object]')).toHaveCount(0)
})

// Inside a v-chip-group, VChip only applies `color` while selected — the tag
// bar must use base-color to keep unselected tags colored.
test('tag bar chips are colored and action buttons show tooltips', async ({ page }) => {
  const data = makeDefaultMockData()
  data.settings.datasets.tagBar.tags = ['review', 'favorite']
  await bootGallery(page, data)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const chip = page.locator('.v-chip-group .v-chip').first()
  await expect(chip).toBeVisible()
  // tagColor('favorite') — hashed into a hue at a fixed saturation/lightness so
  // every chip lands in one readable band, with a foreground picked by
  // luminance rather than inherited from the surroundings.
  const { bg, fg } = await chip.evaluate((el) => {
    const style = getComputedStyle(el)
    return { bg: style.backgroundColor, fg: style.color }
  })
  expect(bg).not.toBe('rgba(0, 0, 0, 0)')
  expect(fg).toBe('rgb(255, 255, 255)')

  await page.locator('.mdi-plus').first().hover()
  await expect(page.getByText(/save .* series as a new dataset/i)).toBeVisible()
})

// V3 v-btn defaults to the "elevated" variant, so the icon buttons rendered a
// raised grey box when disabled; they must use variant="text".
test('dataset action icon buttons are flat, not elevated', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // Disabled by default (no dataset selected) — the case that showed the grey box.
  const removeBtn = page.locator('.mdi-folder-minus-outline').locator('xpath=ancestor::button')
  await expect(removeBtn).toBeDisabled()
  await expect(removeBtn).toHaveClass(/v-btn--variant-text/)
  await expect(removeBtn).not.toHaveClass(/v-btn--variant-elevated/)
})

// An nnunet-style workflow_form field with an empty oneOf ([]) makes ajv reject
// the schema and blank the whole dialog; normalizeV2Schema strips it.
test('workflow dialog: a workflow_form with an empty oneOf renders instead of blanking', async ({
  page,
}) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  // WorkflowExecution client endpoints (absent from the default gallery mock;
  // the catch-all would return {} and break the dialog's boot chain).
  const DAG = 'nnunet-predict'
  const jsonRoute = (body: unknown) => (r: import('@playwright/test').Route) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  await page.route('**/kaapana-backend/client/get-kaapana-instances', jsonRoute([
    { instance_name: 'local', remote: false, allowed_dags: [DAG] },
  ]))
  await page.route('**/kaapana-backend/client/get-dags', jsonRoute([DAG]))
  await page.route('**/kaapana-backend/client/get-ui-form-schemas', jsonRoute({
    [DAG]: {
      workflow_form: {
        type: 'object',
        properties: {
          tasks: {
            title: 'No tasks are available in this project!',
            description: 'You first have to install a task with nnunet-install-model.',
            oneOf: [],
            type: 'string',
            readOnly: false,
            required: true,
          },
        },
      },
    },
  }))

  const consoleErrors: string[] = []
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text())
  })
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await page.goto(VIEW_PATH)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // All series count as selected by default, so Start Workflow is enabled.
  await page.locator('.mdi-play').first().click()
  await expect(page.getByRole('heading', { name: 'Workflow Execution' })).toBeVisible()

  await expect(page.getByText('No tasks are available in this project!').first()).toBeVisible()
  expect(pageErrors).toHaveLength(0)
  expect(consoleErrors.join('\n')).not.toContain('non-empty array')
})

test('series loading shows the skeleton animation', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)
  // Delay the series query so the loading state is observable.
  await page.route(/\/kaapana-backend\/dataset\/series$/, async (r) => {
    await new Promise((res) => setTimeout(res, 3000))
    return r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data.seriesUids),
    })
  })
  await page.goto(VIEW_PATH)
  await expect(page.locator('.v-skeleton-loader').first()).toBeVisible()
  await expect(page.getByText('CT Thorax')).toBeVisible()
})

// ConfirmationDialog took `:show` one-way, so an ESC/outside-click dismiss left
// the parent flag stuck at true and the dialog could never reopen.
test('a dismissed confirmation dialog can be reopened (v-model stays in sync)', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.locator('.mdi-folder-edit-outline').click()
  const editDialog = page
    .locator('.v-overlay.v-dialog')
    .filter({ has: page.getByRole('cell', { name: 'nsclc', exact: true }) })
  await expect(editDialog).toBeVisible()

  const confirmOverlay = page.locator('.v-overlay.v-dialog').filter({ hasText: 'Delete dataset' })
  const confirm = page.getByText('Delete dataset “my-private”?')

  await page.locator('.mdi-delete').first().click()
  await expect(confirm).toBeVisible()
  // Vuetify demotes the parent overlay's globalTop in a deferred tick; ESC in
  // that window closes BOTH dialogs (flake). scroll-blocked lands on the confirm
  // in the same tick, so waiting for it means the stack has settled.
  await expect(confirmOverlay).toHaveClass(/v-overlay--scroll-blocked/)
  await page.keyboard.press('Escape')
  await expect(confirm).toBeHidden()
  // Asserting only that the confirm closed can't tell "child closed" from "both did".
  await expect(editDialog).toBeVisible()

  // Scoped to the parent so the click cannot resolve against another overlay.
  await editDialog.locator('.mdi-delete').first().click()
  await expect(confirm).toBeVisible()
})

// route.query is already decoded by vue-router; a second decodeURIComponent
// threw URIError on a literal '%' in a deep link and the search never ran.
test('a deep-link query string with a literal % is applied, not double-decoded', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  const queryReq = page.waitForRequest(
    (req) =>
      req.method() === 'POST' &&
      /\/dataset\/series$/.test(req.url()) &&
      (req.postData() ?? '').includes('"query":"50%"'),
  )

  // %25 decodes (once, by the router) to '%'.
  await page.goto(VIEW_PATH + '?query_string=50%25')

  const body = (await queryReq).postDataJSON()
  expect(JSON.stringify(body.query)).toContain('"query":"50%"')
  await expect(page.getByText('CT Thorax')).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

// updateData fired its requests with no sequencing, so a slow earlier search
// could resolve last and overwrite a newer one; only the latest may commit.
test('a slow earlier search does not overwrite a newer one (request sequencing)', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  // Keyed on the free-text query: 'stale' is slow, 'fresh' is fast and returns
  // a different series; boot queries get the default set.
  await page.route(/\/dataset\/series$/, async (r) => {
    let q = ''
    try {
      q = JSON.stringify((r.request().postDataJSON() ?? {}).query ?? {})
    } catch {
      /* no JSON body */
    }
    if (q.includes('stale')) {
      await new Promise((res) => setTimeout(res, 2000))
      return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(['1.2.3']) })
    }
    if (q.includes('fresh')) {
      return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(['4.5.6']) })
    }
    return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data.seriesUids) })
  })

  await page.goto(VIEW_PATH)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // Wait until the stale request is actually sent before changing the input.
  const staleReq = page.waitForRequest(
    (req) =>
      req.method() === 'POST' &&
      /\/dataset\/series$/.test(req.url()) &&
      (req.postData() ?? '').includes('stale'),
  )
  await page.getByLabel('Search').first().fill('stale')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await staleReq

  await page.getByLabel('Search').first().fill('fresh')
  await page.getByRole('button', { name: 'Search', exact: true }).click()

  await expect(page.getByText('MR Brain')).toBeVisible()
  await expect(page.getByText('CT Thorax')).toHaveCount(0)

  // Let the slow (stale) response resolve; it must be discarded, not committed.
  await page.waitForTimeout(2500)
  await expect(page.getByText('MR Brain')).toBeVisible()
  await expect(page.getByText('CT Thorax')).toHaveCount(0)
})

// reloadDataset() dropped the access-level argument, so a PRIVATE dataset
// re-looked-up as 'project' returned undefined and later searches showed ALL series.
test('removing series from a private dataset reloads it with access_level=private', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // Select the private dataset; wait for its scoped lookup to fire.
  const selectReload = page.waitForRequest(
    (req) => req.method() === 'GET' && /\/client\/dataset\?.*name=my-private/.test(req.url()),
  )
  await page.getByLabel('Select Dataset').first().click()
  await page.getByRole('option', { name: 'my-private (private)' }).click()
  await selectReload

  const reloadReq = page.waitForRequest(
    (req) =>
      req.method() === 'GET' &&
      /\/client\/dataset\?.*name=my-private/.test(req.url()) &&
      /access_level=private/.test(req.url()),
  )
  await page.locator('.mdi-folder-minus-outline').locator('xpath=ancestor::button').click()
  // The destructive confirmation names the count and the dataset, and its
  // confirm button names the action rather than saying "Confirm".
  await expect(page.getByText(/Remove \d+ series from .+\?/)).toBeVisible()
  await page.getByRole('button', { name: 'Remove', exact: true }).click()

  const url = (await reloadReq).url()
  expect(url).toContain('access_level=private')
})

// The router auth guard swallowed a checkAuth() rejection without calling
// next(), leaving the initial navigation pending and the view permanently blank.
test('the view still mounts when the auth check fails', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  // Fail both the dev static-token file and the prod oauth2 userinfo so
  // checkAuth() rejects regardless of build mode.
  await page.route('**/jsons/testingAuthenticationToken.json', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  await page.route('**/oauth2/userinfo', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )

  await page.goto(VIEW_PATH)

  await expect(page.getByLabel('Select Dataset').first()).toBeVisible()
})

// fetchProjects() swallowed its error and returned undefined, so a ?project_name
// deep link crashed on .find() and aborted onMounted before the datasets loaded.
test('a ?project_name deep link still renders when the project lookup fails', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)

  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  // Fail both branches of the admin/non-admin project lookup.
  await page.route(/\/aii\/(projects|users\/[^/]+\/projects)$/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Projects unavailable' }),
    }),
  )

  await page.goto(`${VIEW_PATH}?project_name=admin`)

  // Both fetchProjects and the project-store consumer now report the failure.
  await expect(page.getByText('Projects unavailable').first()).toBeVisible()
  await expect(page.getByLabel('Select Dataset').first()).toBeVisible()
  await page.getByLabel('Select Dataset').first().click()
  await expect(page.getByRole('option', { name: 'nsclc (project)' })).toBeVisible()
  await expect(page.getByText("doesn't exist or you don't have access")).toHaveCount(0)
  expect(pageErrors).toHaveLength(0)
})
