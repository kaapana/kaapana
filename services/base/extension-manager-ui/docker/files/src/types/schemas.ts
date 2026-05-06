// from extension-manager-service
export interface Repository {
    name: string
    description?: string
    repository_url: string
    id: string
}

// from extension-manager-service
export interface ExtensionManifest {
    name: string
    version: string
    manifest: Record<string, any>
}

// from extension-manager-service
export interface Extension {
    id: string
    repository_id: string
    tag: string
    manifest: Record<string, any>
    status: string
}

// local
export interface CatalogEntry {
  repository: Repository
  extension: ExtensionManifest
}