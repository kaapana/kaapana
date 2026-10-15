import { expect, type Page } from '@playwright/test'
import { installMockBackend, type MockBackend } from './mock-backend'
import type { DocumentEntry } from '../../../src/api/documents'

export async function openView(
  page: Page,
  documents?: DocumentEntry[],
  options?: { seedSettings?: boolean },
): Promise<MockBackend> {
  const backend = await installMockBackend(page, documents, options)
  await page.goto('/')
  await expect(page.getByRole('progressbar', { name: 'Loading documents' })).toBeHidden()
  return backend
}

export function serverError(detail: string, status = 500) {
  return { status, contentType: 'application/json', body: JSON.stringify({ detail }) }
}

export function documentLinks(page: Page) {
  return page.locator('a.v-list-item')
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}
