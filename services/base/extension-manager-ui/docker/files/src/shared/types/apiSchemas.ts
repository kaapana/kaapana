export interface Repository {
  name: string
  description: string
  repository_url: string
  id: string
  built_in: boolean
}

export interface CreateRepositoryRequest {
  name: string
  description?: string
  repository_url: string
  username: string
  password: string
}

export interface UpdateRepositoryRequest {
  name?: string
  description?: string
  repository_url?: string
  username?: string
  password?: string
}

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
  | 'updating'
  | 'update_failed'

export type ContentStatus =
  | 'pending'
  | 'installing'
  | 'installation_failed'
  | 'installed'
  | 'uninstalling'
  | 'uninstallation_failed'
  | 'uninstalled'
  | 'updating'
  | 'update_failed'

export interface ContentFile {
  path: string
}

export interface ExtensionContent {
  name: string
  contentType: string
  files: ContentFile[]
}

export interface ExtensionManifest {
  id: string
  name: string
  version: string
  contents: ExtensionContent[]
  dependencies: unknown[]
}

export interface ExtensionManifestResponse {
  repository_id: string
  tag: string
  manifest: ExtensionManifest
}

export interface InstalledContent {
  name: string
  content_type: string
  status: ContentStatus
  location?: string | null
  applied_version?: string | null
}

export interface PendingUpdate {
  repository_id: string
  tag: string
  manifest: ExtensionManifest
}

export interface InstalledExtension {
  id: string
  repository_id: string
  tag: string
  manifest: ExtensionManifest
  pending_update?: PendingUpdate | null
  status: ExtensionStatus
  contents: InstalledContent[]
}
