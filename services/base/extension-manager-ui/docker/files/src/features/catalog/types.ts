import type { ExtensionManifest, Repository } from '@/shared/types/apiSchemas'

export interface CatalogEntry {
  repository: Repository
  tag: string
  manifest: ExtensionManifest
}

export interface CatalogEntryGroup {
  key: string
  repository: Repository
  manifestName: string
  entries: CatalogEntry[]
}

export interface CatalogFilters {
  repositoryIds?: string[]
  search?: string
}

export type InstallAvailability =
  | { kind: 'available'; label: string }
  | { kind: 'retry'; label: string; reason: string }
  | { kind: 'unavailable'; label: string; reason: string }
