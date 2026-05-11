import type { CatalogEntry } from '@/types/schemas'

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

function filterByRepositories(
  entries: CatalogEntry[],
  repositoryIds?: string[],
): CatalogEntry[] {
  if (!repositoryIds?.length) return entries

  return entries.filter((entry) => repositoryIds.includes(entry.repository.id))
}
