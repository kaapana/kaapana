import type { Page, Route, WebSocketRoute } from '@playwright/test'
import type { DocumentEntry } from '../../../src/api/documents'

export const DOCUMENTS = '**/documents/'

export function documentEntry(
  path: string,
  modified: string,
  bucket = 'project-2f0c5a1e',
): DocumentEntry {
  return {
    file_id: btoa(path),
    file: {
      bucket,
      path,
      extension: path.split('.').pop()!,
      modification_time: modified,
      size: 1024,
    },
    favicon: null,
    app_name: 'writer',
    action_name: 'edit',
    url: `https://kaapana.example/collabora/browser/dist/cool.html?WOPISrc=wopi/files/${btoa(path)}`,
  }
}

export const defaultDocuments: DocumentEntry[] = [
  documentEntry('reports/summary.docx', '2026-10-01T09:00:00+00:00'),
  documentEntry('reports/2026/q3.xlsx', '2026-09-30T16:45:00+00:00'),
  documentEntry('notes/protocol.odt', '2026-10-05T14:30:00+00:00'),
  documentEntry('welcome.odt', '2026-09-20T08:15:00+00:00'),
]

export interface MockBackend {
  documents: DocumentEntry[]
  socket: () => WebSocketRoute | null
}

export async function installMockBackend(
  page: Page,
  documents: DocumentEntry[] = defaultDocuments,
  { seedSettings = true } = {},
): Promise<MockBackend> {
  const backend: MockBackend = { documents: [...documents], socket: () => current }
  let current: WebSocketRoute | null = null

  if (seedSettings) {
    await page.addInitScript(() => {
      if (!localStorage.getItem('settings'))
        localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
    })
  }
  await page.route(DOCUMENTS, (route: Route) => route.fulfill({ json: backend.documents }))
  await page.routeWebSocket(/\/ws$/, (ws) => {
    current = ws
  })
  return backend
}
