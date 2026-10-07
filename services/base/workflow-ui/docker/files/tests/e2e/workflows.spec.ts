import { test, expect } from '@playwright/test'
import { card, failRoute, openWorkflows } from './fixtures/helpers'
import { defaultMockData } from './fixtures/mock-backend'

test.describe('workflow list', () => {
  test('cards show the latest version with its labels', async ({ page }) => {
    await openWorkflows(page)
    const segmentation = card(page, 'Segmentation')
    await expect(segmentation).toContainText('Provider: DKFZ')
    await expect(segmentation).toContainText('Categories: Segmentation')
    await expect(segmentation).toContainText('Segments organs in CT images.')
    await expect(segmentation.getByRole('combobox', { name: 'Version' })).toHaveValue('v2')
  })

  test('selecting an older version shows that revision', async ({ page }) => {
    await openWorkflows(page)
    const segmentation = card(page, 'Segmentation')
    await segmentation.locator('.v-select').click()
    await page.getByRole('option', { name: 'v1' }).click()
    await expect(segmentation).not.toContainText('Provider: DKFZ')
    await expect(segmentation).toContainText('No description available.')
  })

  test('a workflow without parsed tasks cannot start and says why', async ({ page }) => {
    await openWorkflows(page)
    const anonymization = card(page, 'Anonymization')
    await expect(anonymization.getByRole('button', { name: 'Start' })).toBeDisabled()
    await expect(anonymization).toContainText('Not ready yet')
  })

  test('a failed readiness check offers a retry', async ({ page }) => {
    let fail = true
    await openWorkflows(page, {
      routes: (p) =>
        p.route(/registration-1\/tasks$/, (r) =>
          fail
            ? r.fulfill({ status: 500, body: '{}' })
            : r.fulfill({ contentType: 'application/json', body: JSON.stringify([{ id: 5 }]) }),
        ),
    })
    const registration = card(page, 'Registration')
    await expect(registration).toContainText('Could not check whether this workflow is ready.')
    fail = false
    await registration.getByRole('link', { name: 'Try again' }).click()
    await expect(registration.getByRole('button', { name: 'Start' })).toBeEnabled()
  })

  test('sorting switches between A–Z and Z–A', async ({ page }) => {
    await openWorkflows(page)
    const titles = page.getByTestId('workflow-card').locator('.v-card-title')
    await expect(titles).toHaveText(['Anonymization', 'Registration', 'Segmentation'])
    await page.getByRole('button', { name: /Sort:/ }).click()
    await page.getByText('Name Z–A', { exact: true }).click()
    await expect(titles).toHaveText(['Segmentation', 'Registration', 'Anonymization'])
  })

  test('filters narrow the cards and can be reset', async ({ page }) => {
    await openWorkflows(page)
    await page.getByRole('button', { name: 'Show filters' }).click()
    const panel = page.locator('#workflow-filters')
    await panel.getByText('Partner', { exact: true }).click()
    await expect(page.getByTestId('workflow-card')).toHaveCount(1)
    await expect(card(page, 'Registration')).toBeVisible()

    await panel.getByRole('button', { name: 'Reset filters' }).click()
    await expect(page.getByTestId('workflow-card')).toHaveCount(3)
  })

  test('a search without matches says so and offers to clear the filters', async ({ page }) => {
    await openWorkflows(page)
    await page.getByRole('button', { name: 'Show filters' }).click()
    await page.getByRole('textbox', { name: 'Search workflows' }).fill('does-not-exist')
    const state = page.getByTestId('collection-state')
    await expect(state).toContainText('No workflows match the current filters')
    await state.getByRole('button', { name: 'Clear filters' }).click()
    await expect(page.getByTestId('workflow-card')).toHaveCount(3)
  })
})

test.describe('workflow list states', () => {
  test('an empty platform explains why nothing is listed', async ({ page }) => {
    const data = { ...defaultMockData(), workflows: [] }
    await openWorkflows(page, { data })
    await expect(page.getByTestId('collection-state')).toContainText('No workflows yet')
    await expect(page.getByTestId('collection-state')).toContainText(
      'an administrator installs them',
    )
  })

  test('a failed load shows an error with retry and details instead of an empty list', async ({
    page,
  }) => {
    let fail = true
    await openWorkflows(page, {
      routes: (p) =>
        p.route('**/workflow-api/v1/workflows', (r) =>
          fail
            ? r.fulfill({
                status: 503,
                contentType: 'application/json',
                body: '{"detail":"Database down"}',
              })
            : r.fallback(),
        ),
    })
    const state = page.getByTestId('collection-state')
    await expect(state).toContainText('Could not load the workflows')

    await state.getByRole('button', { name: 'Details' }).click()
    await expect(page.getByRole('dialog')).toContainText('Database down')
    await page.getByRole('dialog').getByRole('button', { name: 'Close' }).click()

    fail = false
    await state.getByRole('button', { name: 'Try again' }).click()
    await expect(page.getByTestId('workflow-card')).toHaveCount(3)
  })

  test('a failed refresh keeps the cards and reports the failure', async ({ page }) => {
    await openWorkflows(page)
    await expect(page.getByTestId('workflow-card')).toHaveCount(3)
    await failRoute(page, '**/workflow-api/v1/workflows', 'Database down')
    await page.getByRole('button', { name: 'Refresh' }).click()
    await expect(page.locator('.vue-notification-wrapper')).toContainText(
      'Could not refresh the workflows',
    )
    await expect(page.getByTestId('workflow-card')).toHaveCount(3)
  })
})
