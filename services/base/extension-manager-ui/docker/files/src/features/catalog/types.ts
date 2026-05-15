import type { ExtensionManifest, Repository } from '@/shared/types/apiSchemas'

export interface ExtensionManifestFilters {
  tags?: string[]
}

export interface CatalogEntry {
  repository: Repository
  repository_id: string
  tag: string
  manifest: ExtensionManifest
}

export interface CatalogEntryGroup {
  repository: Repository
  manifestName: string
  entries: CatalogEntry[]
}
