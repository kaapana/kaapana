import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('load more root results appends the next page', async ({ page }) => {
  const data = structuredClone(defaultMockData)
  data.root.nextContinuationToken = 'root-page-2'
  data.pages['root-page-2'] = {
    items: [{ name: 'run-final-230103', path: 'run-final-230103/', children: [] }],
    nextContinuationToken: null,
  }
  await seedShellState(page)
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()

  const pageReq = page.waitForRequest((r) => r.url().includes('continuation_token=root-page-2'))
  await page.getByRole('button', { name: 'Load more root results' }).click()
  await pageReq

  await expect(page.getByText('run-final-230103')).toBeVisible()
  // Appends, not replaces -- page 1 must survive. Every other assertion in this
  // test still passes if the concat becomes a plain assignment.
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()
  // The button disappears once the last page has no further token.
  await expect(page.getByRole('button', { name: 'Load more root results' })).toHaveCount(0)
})

test('load more within a folder appends the next page of children', async ({ page }) => {
  const data = structuredClone(defaultMockData)
  data.children['nnunet-training-230101/'].nextContinuationToken = 'nnunet-page-2'
  data.pages['nnunet-page-2'] = {
    items: [
      {
        name: 'confusion-matrix.png',
        path: 'nnunet-training-230101/confusion-matrix.png',
        file: 'png',
        url: '/minio-console/download/results/nnunet-training-230101/confusion-matrix.png',
      },
    ],
    nextContinuationToken: null,
  }
  await seedShellState(page)
  await installMockBackend(page, data)
  await page.goto(VIEW_PATH)

  await page.getByText('nnunet-training-230101').click()
  await expect(page.getByText('report.html')).toBeVisible()

  const pageReq = page.waitForRequest(
    (r) => r.url().includes('continuation_token=nnunet-page-2') && r.url().includes('prefix=nnunet-training-230101'),
  )
  await page.getByRole('button', { name: 'Load more', exact: true }).click()
  await pageReq

  await expect(page.getByText('confusion-matrix.png')).toBeVisible()
  // Same append-not-replace property one level down, on item.children.
  await expect(page.getByText('report.html')).toBeVisible()
})
