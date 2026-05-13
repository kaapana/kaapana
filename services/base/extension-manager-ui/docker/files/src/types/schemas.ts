// from extension-manager-service
export interface Repository {
    name: string
    description?: string
    repository_url: string
    id: string
}

// from extension-manager-service
export interface CreateRepositoryRequest {
    name: string
    description?: string
    repository_url: string
    authentication: string
}

// from extension-manager-service
export interface UpdateRepositoryRequest {
    name?: string
    description?: string
    repository_url?: string
    authentication?: string
}

// local query params for /repositories/{id}/extensionManifests
export interface ExtensionManifestFilters {
    tags?: string[]
}

// from extension-manager-service
export type ExtensionStatus =
    | 'pending'
    | 'pulling'
    | 'pulling_failed'
    | 'installing'
    | 'installing_failed'
    | 'installed'
    | 'uninstalling'
    | 'uninstalled'
    | 'uninstalling_failed'

// from extension-manager-service
export type ContentStatus =
    | 'pending'
    | 'installing'
    | 'installation_failed'
    | 'installed'
    | 'uninstalling'
    | 'uninstallation_failed'
    | 'uninstalled'

// from extension-manager-service
export interface ContentFile {
    path: string
}

// from extension-manager-service
export interface ExtensionContent {
    name: string
    contentType: string
    files: ContentFile[]
}

// from extension-manager-service
export interface ExtensionManifest {
    name: string
    version: string
    contents: ExtensionContent[]
    dependencies: unknown[]
}

// from extension-manager-service
export interface ExtensionManifestResponse {
    repository_id: string
    tag: string
    manifest: ExtensionManifest
}

// from extension-manager-service
export interface InstalledContent {
    name: string
    content_type: string
    status: ContentStatus
}

// from extension-manager-service
export interface InstalledExtension {
    id: string
    repository_id: string
    tag: string
    manifest: ExtensionManifest
    status: ExtensionStatus
    contents: InstalledContent[]
}

// local
export interface CatalogEntry {
  repository: Repository
  repository_id: string
  tag: string
  manifest: ExtensionManifest
}

// local
export interface CatalogEntryGroup {
  repository: Repository
  manifestName: string
  entries: CatalogEntry[]
}

// local
export interface RepositoryFormState {
  name: string
  description: string
  repository_url: string
  authentication: string
}
