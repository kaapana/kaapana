import type { Page, Route } from '@playwright/test'

export const VIEW_PATH = '/extension-manager-ui/'

export interface RepositoryMock {
  id: string
  name: string
  description: string
  repository_url: string
}

export interface ManifestMock {
  id: string
  name: string
  version: string
  contents: { name: string; contentType: string; files: { path: string }[] }[]
  dependencies: unknown[]
}

export interface ManifestResponseMock {
  repository_id: string
  tag: string
  manifest: ManifestMock
}

export interface InstalledContentMock {
  name: string
  content_type: string
  status: string
  location?: string | null
}

export interface InstalledExtensionMock {
  id: string
  repository_id: string
  tag: string
  manifest: ManifestMock
  status: string
  contents: InstalledContentMock[]
}

export interface MockData {
  repositories: RepositoryMock[]
  manifests: Record<string, ManifestResponseMock[]>
  extensions: InstalledExtensionMock[]
}

export const PUBLIC_REPO: RepositoryMock = {
  id: '11111111-1111-1111-1111-111111111111',
  name: 'kaapana-public',
  description: 'Official Kaapana extensions',
  repository_url: 'https://registry.example.com/kaapana/extensions',
}

export const LAB_REPO: RepositoryMock = {
  id: '22222222-2222-2222-2222-222222222222',
  name: 'lab-internal',
  description: '',
  repository_url: 'https://registry.lab.example.org/team/extensions',
}

export function manifest(
  name: string,
  version: string,
  id: string,
  contents = [`${name}-workflow`],
): ManifestMock {
  return {
    id,
    name,
    version,
    contents: contents.map((content) => ({
      name: content,
      contentType: 'workflow-v1',
      files: [{ path: 'workflow_definition.py' }, { path: 'workflow.json' }],
    })),
    dependencies: [],
  }
}

export function manifestResponse(
  repository: RepositoryMock,
  value: ManifestMock,
): ManifestResponseMock {
  return { repository_id: repository.id, tag: `${value.id}-v${value.version}`, manifest: value }
}

export const NNUNET_V1 = manifest('nnunet', '1.0.0', 'aaaaaaaa-0000-0000-0000-000000000001')
export const NNUNET_V11 = manifest('nnunet', '1.1.0', 'aaaaaaaa-0000-0000-0000-000000000001')
export const TOTALSEG = manifest(
  'totalsegmentator',
  '2.0.0',
  'bbbbbbbb-0000-0000-0000-000000000002',
)
export const RADIOMICS = manifest('radiomics', '0.3.0', 'cccccccc-0000-0000-0000-000000000003')

export function installation(
  repository: RepositoryMock,
  value: ManifestMock,
  status: string,
  id: string,
  contentStatus = status === 'installed' ? 'installed' : 'pending',
): InstalledExtensionMock {
  return {
    id,
    repository_id: repository.id,
    tag: `${value.id}-v${value.version}`,
    manifest: value,
    status,
    contents: value.contents.map((content) => ({
      name: content.name,
      content_type: content.contentType,
      status: contentStatus,
      location: null,
    })),
  }
}

export function defaultMockData(): MockData {
  return {
    repositories: [PUBLIC_REPO, LAB_REPO],
    manifests: {
      [PUBLIC_REPO.id]: [
        manifestResponse(PUBLIC_REPO, NNUNET_V1),
        manifestResponse(PUBLIC_REPO, NNUNET_V11),
        manifestResponse(PUBLIC_REPO, TOTALSEG),
      ],
      [LAB_REPO.id]: [manifestResponse(LAB_REPO, RADIOMICS)],
    },
    extensions: [
      installation(PUBLIC_REPO, TOTALSEG, 'installed', 'eeeeeeee-0000-0000-0000-000000000001'),
      installation(
        LAB_REPO,
        RADIOMICS,
        'installing_failed',
        'eeeeeeee-0000-0000-0000-000000000002',
        'installation_failed',
      ),
    ],
  }
}

function json(body: unknown, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(body) }
}

let nextId = 1000

export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
  })
}

export async function installMockBackend(
  page: Page,
  data: MockData = defaultMockData(),
  { seedSettings = true }: { seedSettings?: boolean } = {},
): Promise<MockData> {
  if (seedSettings) await seedShellState(page)

  await page.route('**/extensions-api/**', async (route: Route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace(/^.*\/extensions-api/, '')
    const method = request.method()

    if (path === '/repositories' && method === 'GET') return route.fulfill(json(data.repositories))
    if (path === '/repositories' && method === 'POST') {
      const body = request.postDataJSON()
      const created: RepositoryMock = {
        id: `99999999-0000-0000-0000-${String(nextId++).padStart(12, '0')}`,
        name: body.name,
        description: body.description ?? '',
        repository_url: body.repository_url,
      }
      data.repositories.push(created)
      return route.fulfill(json(created, 201))
    }

    const manifests = path.match(/^\/repositories\/([^/]+)\/extensionManifests$/)
    if (manifests && method === 'GET')
      return route.fulfill(json(data.manifests[manifests[1]!] ?? []))

    const repository = path.match(/^\/repositories\/([^/]+)$/)
    if (repository && method === 'PUT') {
      const body = request.postDataJSON()
      const existing = data.repositories.find((entry) => entry.id === repository[1])
      if (!existing) return route.fulfill(json({ detail: 'Repository not found' }, 404))
      if (body.name !== undefined && body.name !== null) existing.name = body.name
      if (body.description !== undefined && body.description !== null)
        existing.description = body.description
      if (body.repository_url !== undefined && body.repository_url !== null)
        existing.repository_url = body.repository_url
      return route.fulfill(json(existing))
    }
    if (repository && method === 'DELETE') {
      data.repositories = data.repositories.filter((entry) => entry.id !== repository[1])
      data.extensions = data.extensions.filter((entry) => entry.repository_id !== repository[1])
      return route.fulfill({ status: 204 })
    }

    if (path === '/extensions' && method === 'GET') return route.fulfill(json(data.extensions))
    if (path === '/extensions/install' && method === 'POST') {
      const repositoryId = url.searchParams.get('repository_id')!
      const tag = url.searchParams.get('tag')!
      const response = (data.manifests[repositoryId] ?? []).find((entry) => entry.tag === tag)
      if (!response)
        return route.fulfill(json({ detail: `Extension with tag ${tag} not found` }, 404))
      const existing = data.extensions.find(
        (entry) => entry.repository_id === repositoryId && entry.tag === tag,
      )
      if (existing) {
        existing.status = 'pending'
        return route.fulfill(json(existing, 201))
      }
      const repositoryMock = data.repositories.find((entry) => entry.id === repositoryId)!
      const created = installation(
        repositoryMock,
        response.manifest,
        'pending',
        `dddddddd-0000-0000-0000-${String(nextId++).padStart(12, '0')}`,
      )
      data.extensions.push(created)
      return route.fulfill(json(created, 201))
    }

    const uninstall = path.match(/^\/extensions\/([^/]+)\/uninstall$/)
    if (uninstall && method === 'POST') {
      const existing = data.extensions.find((entry) => entry.id === uninstall[1])
      if (!existing) return route.fulfill(json({ detail: 'Extension not found' }, 404))
      existing.status = 'uninstalling'
      return route.fulfill(json(null, 202))
    }

    return route.fulfill(json({ detail: `Unmocked ${method} ${path}` }, 501))
  })

  return data
}
