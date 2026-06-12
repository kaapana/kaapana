import type { CatalogEntry, CatalogEntryGroup } from '@/features/catalog/types'

export interface CatalogFilters {
  repositoryIds?: string[]
  search?: string
}

export function applyCatalogFilters(
  entries: CatalogEntry[],
  filters: CatalogFilters,
): CatalogEntry[] {
  let filteredEntries = entries

  filteredEntries = filterBySearch(filteredEntries, filters.search)
  filteredEntries = filterByRepositories(filteredEntries, filters.repositoryIds)

  return filteredEntries
}

function filterBySearch(entries: CatalogEntry[], searchValue?: string): CatalogEntry[] {
  const search = searchValue?.trim().toLowerCase()

  if (!search) return entries

  return entries.filter((entry) =>
    [
      entry.manifest.name,
      entry.manifest.version,
      entry.repository.name,
      entry.repository.repository_url,
    ].some((value) => value.toLowerCase().includes(search)),
  )
}

function filterByRepositories(entries: CatalogEntry[], repositoryIds?: string[]): CatalogEntry[] {
  if (!repositoryIds?.length) return entries

  return entries.filter((entry) => repositoryIds.includes(entry.repository.id))
}

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
    rightEntry.manifest.version.localeCompare(leftEntry.manifest.version, undefined, {
      numeric: true,
      sensitivity: 'base',
    }),
  )
}
