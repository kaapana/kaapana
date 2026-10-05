import { test, expect } from '@playwright/test'
import { defaultMockData, LAB_REPO, PUBLIC_REPO, type MockData } from './fixtures/mock-backend'
import { card, cards, dialog, failRoute, openView, pressEscapeUntil } from './fixtures/helpers'

test.describe('listing', () => {
  test.beforeEach(({ page }) => openView(page))

  test('one card per extension and repository, with its versions and installation state', async ({
    page,
  }) => {
    await expect(cards(page)).toHaveCount(3)

    const nnunet = card(page, 'nnunet')
    await expect(nnunet).toContainText('kaapana-public')
    await expect(nnunet).toContainText('2 versions')
    await expect(nnunet).toContainText('Latest 1.1.0')

    await expect(card(page, 'totalsegmentator')).toContainText('Installed')
    await expect(card(page, 'radiomics')).toContainText('Installation failed')
    await expect(page.getByText('2 repositories')).toBeVisible()
    await expect(page.getByText('4 extension versions')).toBeVisible()
  })

  test('the detail dialog shows source, contents and the raw manifest', async ({ page }) => {
    await card(page, 'nnunet').click()
    const details = dialog(page)

    await expect(details.getByText('nnunet', { exact: true })).toBeVisible()
    await expect(details).toContainText(PUBLIC_REPO.repository_url)
    await expect(details.getByRole('combobox', { name: 'Version' })).toHaveValue('1.1.0')
    await expect(details).toContainText('aaaaaaaa-0000-0000-0000-000000000001-v1.1.0')

    await details.getByRole('button', { name: 'nnunet-workflow' }).click()
    await expect(details).toContainText('workflow-v1')
    await expect(details).toContainText('workflow_definition.py')

    await details.getByRole('button', { name: 'Raw manifest' }).click()
    await expect(details.locator('pre')).toContainText('"version": "1.1.0"')

    await details.getByRole('button', { name: 'Show more' }).click()
    await expect(details).toContainText(PUBLIC_REPO.id)
  })

  test('a card opens from the keyboard, and Escape closes the dialog', async ({ page }) => {
    const nnunet = card(page, 'nnunet')
    await nnunet.focus()
    await page.keyboard.press('Enter')
    await expect(dialog(page)).toBeVisible()

    await pressEscapeUntil(page, () => dialog(page).isHidden())
    await expect(nnunet).toBeFocused()
  })
})

test.describe('filtering', () => {
  test.beforeEach(({ page }) => openView(page))

  test('search matches name, version and repository', async ({ page }) => {
    const search = page.getByRole('textbox', { name: 'Search catalog' })

    await search.fill('total')
    await expect(cards(page)).toHaveCount(1)
    await expect(card(page, 'totalsegmentator')).toBeVisible()

    await search.fill('lab-internal')
    await expect(cards(page)).toHaveCount(1)
    await expect(card(page, 'radiomics')).toBeVisible()
  })

  test('the repository filter narrows to the chosen repositories', async ({ page }) => {
    await page.locator('div[role="combobox"]', { hasText: 'Repositories' }).click()
    await page.getByRole('option', { name: LAB_REPO.name }).click()
    await page.keyboard.press('Escape')

    await expect(cards(page)).toHaveCount(1)
    await expect(card(page, 'radiomics')).toBeVisible()
  })

  test('nothing matching says so and offers to clear the filters', async ({ page }) => {
    await page.getByRole('textbox', { name: 'Search catalog' }).fill('no-such-extension')

    const empty = page.getByTestId('empty-state')
    await expect(empty).toContainText('No extensions match the current filters')
    await empty.getByRole('button', { name: 'Clear filters' }).click()
    await expect(cards(page)).toHaveCount(3)
  })
})

test.describe('empty and failure states', () => {
  test('no repositories yet points to adding one', async ({ page }) => {
    const data: MockData = { repositories: [], manifests: {}, extensions: [] }
    await openView(page, 'catalog', data, { waitFor: 'empty' })

    const empty = page.getByTestId('empty-state')
    await expect(empty).toContainText('No repositories registered yet')
    await empty.getByRole('link', { name: 'Add a repository' }).click()
    await expect(page).toHaveURL(/\/repositories$/)
  })

  test('repositories without extensions say nothing is published yet', async ({ page }) => {
    const data: MockData = { ...defaultMockData(), manifests: {} }
    await openView(page, 'catalog', data, { waitFor: 'empty' })

    await expect(page.getByTestId('empty-state')).toContainText('No extensions published yet')
    await expect(page.getByRole('textbox', { name: 'Search catalog' })).toHaveCount(0)
  })

  test('a failed load is an error with retry and details, not an empty catalog', async ({
    page,
  }) => {
    let fail = true
    await openView(page, 'catalog', defaultMockData(), {
      waitFor: 'empty',
      routes: (p) =>
        p.route(/\/extensions-api\/repositories$/, (route) =>
          fail
            ? route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'database unavailable' }),
              })
            : route.fallback(),
        ),
    })

    const empty = page.getByTestId('empty-state')
    await expect(empty).toContainText('Could not load the catalog')
    await empty.getByRole('button', { name: 'Details' }).click()
    const details = dialog(page)
    await expect(details).toContainText('503')
    await expect(details).toContainText('database unavailable')
    await details.getByRole('button', { name: 'Close' }).click()

    fail = false
    await empty.getByRole('button', { name: 'Try again' }).click()
    await expect(cards(page)).toHaveCount(3)
  })

  test('one unreachable repository keeps the others and is named in a warning', async ({
    page,
  }) => {
    await openView(page, 'catalog', defaultMockData(), {
      routes: (p) =>
        failRoute(
          p,
          `/repositories/${LAB_REPO.id}/extensionManifests`,
          'registry unauthorized',
          401,
        ),
    })

    await expect(cards(page)).toHaveCount(2)
    const warning = page.getByTestId('repository-failures')
    await expect(warning).toContainText('"lab-internal"')
    await warning.getByRole('button', { name: 'Details' }).click()
    await expect(dialog(page)).toContainText('registry unauthorized')
  })
})
