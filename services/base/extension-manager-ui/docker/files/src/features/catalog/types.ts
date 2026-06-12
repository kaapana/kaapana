import type { ExtensionManifest, Repository } from '@/shared/types/apiSchemas'

export interface ExtensionManifestFilters {
  tags?: string[]
}

export interface CatalogEntry {
  repository: Repository
  tag: string
  manifest: ExtensionManifest
}

export interface CatalogEntryGroup {
  repository: Repository
  manifestName: string
  entries: CatalogEntry[]
}
