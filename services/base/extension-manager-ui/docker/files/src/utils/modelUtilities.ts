import type { ExtensionManifest } from '@/types/schemas'

export function createMockCatalogEntryTag(manifest: ExtensionManifest): string {
  return `${manifest.name}-${manifest.version}`
}