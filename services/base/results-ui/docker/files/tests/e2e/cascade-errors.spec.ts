import { test, expect } from '@playwright/test'
import {
  defaultMockData,
  installMockBackend,
  seedShellState,
  VIEW_PATH,
  type MockTreeNode,
} from './fixtures/mock-backend'

// Regression guards for the folder-cascade failure and race paths.

const bigFolder = (name: string): MockTreeNode => ({
  name,
  path: `${name}/`,
  file: false,
  children: [],
  hasChildren: true,
})
const bigFiles = (name: string, count: number): MockTreeNode[] =>
  Array.from({ length: count }, (_, i) => ({
    name: `f${i}.html`,
    path: `${name}/f${i}.html`,
    file: 'html',
    children: [],
    hasChildren: false,
    url: `/minio-console/download/results/${name}/f${i}.html`,
  }))

const emptyFolders = (parent: string, count: number): MockTreeNode[] =>
  Array.from({ length: count }, (_, i) => ({
    name: `e${i}`,
    path: `${parent}e${i}/`,
    file: false,
    children: [],
    hasChildren: true,
  }))

async function stubFiles(context: import('@playwright/test').BrowserContext) {
  await context.route('**/minio-console/**', (r) =>
    r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>stub</body></html>' }),
  )
}

// A continuation page failing mid-cascade must be terminal, not an infinite
// retry storm. Before the fix this hit the endpoint ~hundreds of times/sec.
test('a failed continuation page mid-cascade stops instead of storming', async ({
  page,
  context,
}) => {
  await seedShellState(page)
  await installMockBackend(page)
  let tokenRequests = 0
  // Later route wins: fail every continuation_token request with a 500.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    if (new URL(r.request().url()).searchParams.get('continuation_token')) {
      tokenRequests += 1
      return r.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' })
    }
    return r.fallback()
  })
  await stubFiles(context)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('overview.html')).toBeVisible()

  // batch-run-230104 pages part-b via a continuation token that now 500s.
  const folderCheckbox = page
    .locator('.v-list-item', { hasText: 'batch-run-230104' })
    .getByRole('checkbox')
    .first()
  await folderCheckbox.check()

  // The search field's VField keeps a hidden progress-linear in the DOM, so
  // match only a visible one -- that is the cascade bar.
  await expect(folderCheckbox).not.toBeChecked()
  await expect(page.locator('.v-progress-linear:visible')).toHaveCount(0)
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)

  // Let any lingering storm accumulate, then assert it never happened.
  await page.waitForTimeout(1000)
  expect(tokenRequests).toBeLessThanOrEqual(2)
})

test('unchecking a folder mid-cascade opens nothing', async ({ page, context }) => {
  await seedShellState(page)
  await installMockBackend(page)
  // Delay the folder's children so the uncheck lands while the fetch is in flight.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', async (r) => {
    if (new URL(r.request().url()).searchParams.get('prefix') === 'nnunet-training-230101/') {
      await new Promise((res) => setTimeout(res, 1200))
    }
    return r.fallback()
  })
  await stubFiles(context)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('overview.html')).toBeVisible()

  const folderCheckbox = page
    .locator('.v-list-item', { hasText: 'nnunet-training-230101' })
    .getByRole('checkbox')
    .first()
  await folderCheckbox.check()
  await page.waitForTimeout(300)
  await folderCheckbox.uncheck()

  // Wait out the delayed fetch; its completion must be discarded.
  await page.waitForTimeout(1500)
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
  await expect(folderCheckbox).not.toBeChecked()
})

// The second folder is rejected (reverted); the first stays honored.
test('a second large-folder check does not clobber the pending confirm', async ({
  page,
  context,
}) => {
  const data = structuredClone(defaultMockData)
  data.root.items = [bigFolder('big-a'), bigFolder('big-b')]
  data.children = {
    'big-a/': { items: bigFiles('big-a', 12), nextContinuationToken: null },
    'big-b/': { items: bigFiles('big-b', 12), nextContinuationToken: null },
  }
  await seedShellState(page)
  await installMockBackend(page, data)
  // Delay big-a so big-b's dialog opens first; big-a completes with a dialog up.
  await page.route('**/kaapana-backend/get-static-website-results-tree**', async (r) => {
    if (new URL(r.request().url()).searchParams.get('prefix') === 'big-a/') {
      await new Promise((res) => setTimeout(res, 1500))
    }
    return r.fallback()
  })
  await stubFiles(context)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('big-a')).toBeVisible()

  const aCheckbox = page.locator('.v-list-item', { hasText: 'big-a' }).getByRole('checkbox').first()
  await aCheckbox.check()
  await page.locator('.v-list-item', { hasText: 'big-b' }).getByRole('checkbox').first().check()

  // big-b's prompt is up; wait out big-a's fetch so its (rejected) cascade runs.
  await expect(page.getByText('Open 12 results?')).toBeVisible()
  await page.waitForTimeout(2000)
  // The late folder was rejected and unchecked; the prompt is still big-b's.
  await expect(aCheckbox).not.toBeChecked()

  await page.getByRole('button', { name: 'Open all' }).click()
  // Exactly one folder's results open -- no clobber, no double.
  await expect(page.locator('.v-expansion-panel')).toHaveCount(12)
  await expect(aCheckbox).not.toBeChecked()
})

// The recursive fetch caps at MAX_CASCADE_FILES (300) results and, separately, at
// MAX_CASCADE_REQUESTS (300) fetches; here the file cap is the one that bites and
// the confirm prompt reflects it. (Not confirmed: avoids rendering 300 iframes.)
test('cascade caps the number of results it will open', async ({ page, context }) => {
  const data = structuredClone(defaultMockData)
  data.root.items = [bigFolder('huge')]
  data.children = { 'huge/': { items: bigFiles('huge', 301), nextContinuationToken: null } }
  await seedShellState(page)
  await installMockBackend(page, data)
  await stubFiles(context)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('huge')).toBeVisible()

  await page.locator('.v-list-item', { hasText: 'huge' }).getByRole('checkbox').first().check()

  await expect(page.getByText('Open 300 results?')).toBeVisible()
})

// Only .html objects become files, so a subtree of result-less folders never
// reaches the file cap: the request cap is the only thing that ends the walk.
test('a result-less subtree stops at the request cap and says so', async ({ page, context }) => {
  test.setTimeout(60_000) // draining the whole budget is ~300 sequential requests
  const data = structuredClone(defaultMockData)
  data.root.items = [bigFolder('sprawl')]
  const branches = emptyFolders('sprawl/', 25)
  data.children = { 'sprawl/': { items: branches, nextContinuationToken: null } }
  data.pages = {}
  // A folder of non-.html objects lists no results yet still pages: 13 requests
  // per branch, so the walk crosses the cap without ever producing a file.
  for (const { path } of branches) {
    data.children[path] = { items: [], nextContinuationToken: `${path}p0` }
    for (let i = 0; i < 12; i += 1) {
      const next = i < 11 ? `${path}p${i + 1}` : null
      data.pages[`${path}p${i}`] = { items: [], nextContinuationToken: next }
    }
  }
  await seedShellState(page)
  await installMockBackend(page, data)
  let treeRequests = 0
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    treeRequests += 1
    return r.fallback()
  })
  await stubFiles(context)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('sprawl')).toBeVisible()

  await page.locator('.v-list-item', { hasText: 'sprawl' }).getByRole('checkbox').first().check()

  await expect(page.getByText('Too many results')).toBeVisible({ timeout: 30_000 })
  await expect(page.locator('.v-expansion-panel')).toHaveCount(0)
  // The root listing plus at most MAX_CASCADE_REQUESTS (300) cascade fetches.
  expect(treeRequests).toBeLessThanOrEqual(301)
})

// Continuation pages burn requests without yielding files either; a partially
// drained folder must keep its token so the interactive button still works.
test('endless continuation pages stop at the request cap and keep Load more', async ({
  page,
  context,
}) => {
  test.setTimeout(60_000)
  const data = structuredClone(defaultMockData)
  data.root.items = [bigFolder('paged')]
  data.children = { 'paged/': { items: [], nextContinuationToken: 'page-0' } }
  data.pages = Object.fromEntries(
    Array.from({ length: 1000 }, (_, i) => [
      `page-${i}`,
      { items: [], nextContinuationToken: `page-${i + 1}` },
    ]),
  )
  await seedShellState(page)
  await installMockBackend(page, data)
  let treeRequests = 0
  await page.route('**/kaapana-backend/get-static-website-results-tree**', (r) => {
    treeRequests += 1
    return r.fallback()
  })
  await stubFiles(context)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('paged')).toBeVisible()

  await page.locator('.v-list-item', { hasText: 'paged' }).getByRole('checkbox').first().check()

  await expect(page.getByText('Too many results')).toBeVisible({ timeout: 30_000 })
  expect(treeRequests).toBeLessThanOrEqual(301)
  await expect(page.getByRole('button', { name: 'Load more', exact: true })).toBeVisible()
})
