import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'
import type { MenuResponse, MenuEntry } from '../../src/types/menu'

function entry(id: string, path: string, over: Partial<MenuEntry> = {}): MenuEntry {
  return {
    type: 'entry',
    id,
    label: id,
    icon: 'mdi-test',
    path,
    target: 'iframe',
    project: 'path',
    default: false,
    order: 0,
    ...over,
  }
}

// Menu in which every legacy-redirect target resolves: the redirect rewrites
// the path, then the router's beforeEach must resolve /workflows/<id> against a
// real entry or it bounces back to "/". So all seven live under "workflows".
const redirectMenu: MenuResponse = {
  items: [
    entry('extensions', '/extensions-ui', { default: true }),
    {
      type: 'section',
      id: 'workflows',
      label: 'Workflows',
      icon: 'mdi-clipboard-flow',
      order: 1,
      entries: [
        entry('datasets', '/data-gallery-ui'),
        entry('data-upload', '/data-upload-ui'),
        entry('workflow-execution', '/workflow-execution-ui'),
        entry('workflows', '/workflow-list-ui'),
        entry('results-browser', '/results-ui'),
        entry('runner-instances', '/federated-ui'),
        entry('tasks', '/app-ui/tasks'),
      ],
    },
  ],
}

const legacyCases: [from: string, to: string][] = [
  ['/datasets', '/workflows/datasets'],
  ['/data-upload', '/workflows/data-upload'],
  ['/workflow-execution', '/workflows/workflow-execution'],
  ['/workflows', '/workflows/workflows'],
  ['/results-browser', '/workflows/results-browser'],
  ['/runner-instances', '/workflows/runner-instances'],
  ['/active-applications', '/workflows/tasks'],
  ['/workflows/active-applications', '/workflows/tasks'],
]

test.describe('legacy monolith-route redirects', () => {
  test.beforeEach(async ({ page }) => {
    await installMockBackend(page, { ...defaultMockData, menu: redirectMenu })
    await stubView(page, '/data-gallery-ui')
    await stubView(page, '/extensions-ui')
  })

  for (const [from, to] of legacyCases) {
    test(`${from} -> ${to}`, async ({ page }) => {
      await page.goto(from)
      await expect(page).toHaveURL(new RegExp(to.replace(/\//g, '\\/') + '$'))
    })
  }

  test('preserves the query string across the redirect and into the iframe', async ({ page }) => {
    await page.goto('/datasets?foo=bar&x=1')
    await expect(page).toHaveURL(/\/workflows\/datasets\?foo=bar&x=1$/)
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
      'src',
      '/project/admin/data-gallery-ui?foo=bar&x=1',
    )
  })

  test('a project-prefixed pre-split bookmark redirects within the same project', async ({
    page,
  }) => {
    // Pre-split bookmarks carry the project prefix, which the unscoped
    // route-record redirects never match; the guard must map them itself.
    await stubView(page, '/app-ui')
    await page.goto('/project/admin/workflows/active-applications?x=1')
    await expect(page).toHaveURL(/\/project\/admin\/workflows\/tasks\?x=1$/)
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
      'src',
      '/project/admin/app-ui/tasks?x=1',
    )
  })
})

test.describe('shell routing on the default menu', () => {
  test.beforeEach(async ({ page }) => {
    await installMockBackend(page)
    await stubView(page, '/data-gallery-ui')
    await stubView(page, '/data-upload-ui')
    await stubView(page, '/extensions-ui')
    await stubView(page, '/docs/')
  })

  test('"/" resolves to the backend-flagged default entry', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', '/project/admin/data-gallery-ui')
  })

  test('/web/<section>/<entry> bookmark strips onto the canonical route', async ({ page }) => {
    await page.goto('/web/workflows/data-upload?a=1')
    await expect(page).toHaveURL(/\/workflows\/data-upload\?a=1$/)
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
      'src',
      '/project/admin/data-upload-ui?a=1',
    )
  })

  test('/web/-/<entry> (NO_SECTION) strips to a top-level route', async ({ page }) => {
    // "extensions" is a top-level entry that is NOT a legacy-redirect key, so
    // it exercises the NO_SECTION strip without bouncing through another redirect.
    await page.goto('/web/-/extensions')
    await expect(page).toHaveURL(/\/extensions$/)
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', '/project/admin/extensions-ui')
  })

  test('unknown route falls back to the default view', async ({ page }) => {
    await page.goto('/does/not/exist')
    await expect(page).toHaveURL(/\/project\/admin$/)
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', '/project/admin/data-gallery-ui')
  })

  test('tab-target entry is not reachable as an in-shell route (falls back)', async ({ page }) => {
    await page.goto('/system/monitoring')
    await expect(page).toHaveURL(/\/project\/admin$/)
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute('src', '/project/admin/data-gallery-ui')
  })

  test('/help loads the docs iframe (no menu entry required)', async ({ page }) => {
    await page.goto('/help')
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
      'src',
      '/docs/faq_root.html',
    )
  })

  test('rest segments are appended to the iframe path with the query preserved', async ({
    page,
  }) => {
    await page.goto('/workflows/data-upload/some/path?x=1')
    await expect(page.locator('iframe.kaapana-iframe')).toHaveAttribute(
      'src',
      '/project/admin/data-upload-ui/some/path?x=1',
    )
  })
})

test.describe('project-scoped shell URLs', () => {
  test.beforeEach(async ({ page }) => {
    await installMockBackend(page)
    await stubView(page, '/data-gallery-ui')
  })

  test('"/" is re-targeted onto the default project prefix', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/project\/admin$/)
  })

  test('unprefixed deep links keep their path under the project prefix', async ({ page }) => {
    await page.goto('/extensions?foo=bar')
    await expect(page).toHaveURL(/\/project\/admin\/extensions\?foo=bar$/)
  })

  test('a deep link with a project prefix selects that project', async ({ page }) => {
    await page.goto('/project/resb/datasets')
    await expect(page).toHaveURL(/\/project\/resb\/datasets$/)
    await expect
      .poll(() => page.evaluate(() => JSON.parse(localStorage['project'] ?? 'null')?.short_id))
      .toBe('resb')
  })

  test('an unknown project slug falls back to the selected project, query preserved', async ({
    page,
  }) => {
    await page.goto('/project/does-not-exist/datasets?foo=bar')
    await expect(page).toHaveURL(/\/project\/admin\/datasets\?foo=bar$/)
  })

  test('the shell scopes its own backend calls to the URL prefix on first boot', async ({
    page,
  }) => {
    // The pathname-based interceptor can only scope once the redirect has moved
    // "/" onto /project/admin — guaranteed by awaiting router.isReady() before
    // mount. The boot-time settings GET is the deterministic witness.
    const settingsReq = page.waitForRequest(
      (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'GET',
    )
    await page.goto('/')
    expect(new URL((await settingsReq).url()).pathname).toBe(
      '/project/admin/kaapana-backend/settings',
    )
  })
})
