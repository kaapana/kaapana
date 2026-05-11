import type { CatalogEntry, CatalogEntryGroup } from '@/types/schemas'

export function groupCatalogEntries(entries: CatalogEntry[]): CatalogEntryGroup[] {
  const groups = new Map<string, CatalogEntryGroup>()

  for (const entry of entries) {
    const groupKey = `${entry.repository.id}:${entry.manifest.name}`
    const existingGroup = groups.get(groupKey)

    if (existingGroup) {
      existingGroup.entries.push(entry)
    } else {
      groups.set(groupKey, {
        repository: entry.repository,
        manifestName: entry.manifest.name,
        entries: [entry],
      })
    }
  }

  return Array.from(groups.values()).map((group) => ({
    ...group,
    entries: sortEntriesByVersion(group.entries),
  }))
}

function sortEntriesByVersion(entries: CatalogEntry[]): CatalogEntry[] {
  return [...entries].sort((leftEntry, rightEntry) =>
    rightEntry.manifest.version.localeCompare(
      leftEntry.manifest.version,
      undefined,
      {
        numeric: true,
        sensitivity: 'base',
      },
    ),
  )
}
