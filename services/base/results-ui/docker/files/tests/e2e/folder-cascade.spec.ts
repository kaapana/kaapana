import { test, expect } from '@playwright/test'
import {
  defaultMockData,
  installMockBackend,
  seedShellState,
  VIEW_PATH,
} from './fixtures/mock-backend'

// Checking a folder's checkbox opens every result file in its subtree; unloaded
// descendants (and continuation pages) are fetched first, >10 results asks first.

test.beforeEach(async ({ page, context }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // The cascade opens many iframes; stub file requests at the context level too.
  await context.route('**/minio-console/**', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>stub</body></html>' }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('overview.html')).toBeVisible()
})

test('checking a small folder opens a panel for each of its files without asking', async ({
  page,
}) => {
  // Expand first so the child rows are visible: this also pins the cascade's
  // programmatic-selection round trip -- the child checkboxes must light up.
  await page.getByText('nnunet-training-230101').click()
  await expect(page.getByText('report.html')).toBeVisible()

  // nnunet-training-230101/ holds 2 files (<= 10): open straight away.
  const folderCheckbox = page
    .locator('.v-list-item', { hasText: 'nnunet-training-230101' })
    .getByRole('checkbox')
    .first()
  await folderCheckbox.check()

  await expect(page.locator('.v-expansion-panel')).toHaveCount(2)
  await expect(folderCheckbox).toBeChecked()
  await expect(
    page.locator('.v-list-item', { hasText: 'report.html' }).getByRole('checkbox').first(),
  ).toBeChecked()
  await expect(page.getByText(/Open \d+ results\?/)).toHaveCount(0)
})

test('checking a large folder asks before opening, then opens all on confirm', async ({ page }) => {
  // batch-run-230104/ = 11 files, crossing the >10 threshold only via the
  // unloaded part-b/ subfolder and its continuation page (see the fixture).
  await page
    .locator('.v-list-item', { hasText: 'batch-run-230104' })
    .getByRole('checkbox')
    .first()
    .check()

  await expect(page.getByText('Open 11 results?')).toBeVisible()
  // Nothing opened while the dialog is up.
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)

  await page.getByRole('button', { name: 'Open all' }).click()

  await expect(page.getByText('Open 11 results?')).toBeHidden()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(11)
})

test('cancelling the confirm dialog opens nothing and unchecks the folder', async ({ page }) => {
  const folderCheckbox = page
    .locator('.v-list-item', { hasText: 'batch-run-230104' })
    .getByRole('checkbox')
    .first()
  await folderCheckbox.check()

  await expect(page.getByText('Open 11 results?')).toBeVisible()
  await page.getByRole('button', { name: 'Cancel' }).click()

  await expect(page.getByText('Open 11 results?')).toBeHidden()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
  await expect(folderCheckbox).not.toBeChecked()
})

// The real backend rstrips folder paths (no trailing slash) while the default
// mock keeps them, so prove prefix-match + pruning against a slash-less path too.
test('cascades a folder whose path has no trailing slash', async ({ page, context }) => {
  const data = structuredClone(defaultMockData)
  data.root.items = [
    { name: 'run-noslash', path: 'run-noslash', file: false, children: [], hasChildren: true },
  ]
  data.children = {
    'run-noslash': {
      items: [
        {
          name: 'a.html',
          path: 'run-noslash/a.html',
          file: 'html',
          children: [],
          hasChildren: false,
          url: '/minio-console/download/results/run-noslash/a.html',
        },
        {
          name: 'b.html',
          path: 'run-noslash/b.html',
          file: 'html',
          children: [],
          hasChildren: false,
          url: '/minio-console/download/results/run-noslash/b.html',
        },
      ],
      nextContinuationToken: null,
    },
  }
  await seedShellState(page)
  await installMockBackend(page, data)
  await context.route('**/minio-console/**', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>stub</body></html>' }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByText('run-noslash')).toBeVisible()

  const folderCheckbox = page
    .locator('.v-list-item', { hasText: 'run-noslash' })
    .getByRole('checkbox')
    .first()
  await folderCheckbox.check()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(2)

  await folderCheckbox.uncheck()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
})

test('unchecking a cascaded folder removes its result panels', async ({ page }) => {
  const folderCheckbox = page
    .locator('.v-list-item', { hasText: 'nnunet-training-230101' })
    .getByRole('checkbox')
    .first()

  await folderCheckbox.check()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(2)

  await folderCheckbox.uncheck()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Workflow results' })).toBeVisible()
})

// The dialog used to be persistent, so neither Escape nor a click outside it
// did anything and the folder stayed ticked with nothing opened.
test('pressing escape cancels the confirm and unchecks the folder', async ({ page }) => {
  const checkbox = page.locator('.v-list-item', { hasText: 'batch-run-230104' }).getByRole('checkbox').first()
  await checkbox.check()
  await expect(page.getByText('Open 11 results?')).toBeVisible()
  // The dialog takes focus only once it has finished opening; Escape reaches it
  // through the focused element, so a keypress before that would be lost.
  await expect(page.getByRole('button', { name: 'Cancel' })).toBeFocused()

  await page.keyboard.press('Escape')

  await expect(page.getByText('Open 11 results?')).toBeHidden()
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
  await expect(checkbox).not.toBeChecked()
})

// The safe action takes focus, so confirming a large open is deliberate.
test('the confirm dialog opens with the safe action focused', async ({ page }) => {
  await page.locator('.v-list-item', { hasText: 'batch-run-230104' }).getByRole('checkbox').first().check()
  await expect(page.getByText('Open 11 results?')).toBeVisible()

  await expect(page.getByRole('button', { name: 'Cancel' })).toBeFocused()
})
