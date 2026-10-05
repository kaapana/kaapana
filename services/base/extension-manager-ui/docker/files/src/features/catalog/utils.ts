import type {
  CatalogEntry,
  CatalogEntryGroup,
  CatalogFilters,
  InstallAvailability,
} from '@/features/catalog/types'
import type { InstalledExtension } from '@/shared/types/apiSchemas'
import { RETRYABLE_INSTALL_STATUSES } from '@/shared/utils/status'

export function applyCatalogFilters(
  entries: CatalogEntry[],
  filters: CatalogFilters,
): CatalogEntry[] {
  return filterByRepositories(filterBySearch(entries, filters.search), filters.repositoryIds)
}

export function hasActiveFilters(filters: CatalogFilters): boolean {
  return Boolean(filters.search?.trim() || filters.repositoryIds?.length)
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

export function catalogGroupKey(entry: CatalogEntry): string {
  return `${entry.repository.id}:${entry.manifest.name}`
}

export function groupCatalogEntries(entries: CatalogEntry[]): CatalogEntryGroup[] {
  const groups = new Map<string, CatalogEntryGroup>()

  for (const entry of entries) {
    const key = catalogGroupKey(entry)
    const existingGroup = groups.get(key)
    if (existingGroup) {
      existingGroup.entries.push(entry)
    } else {
      groups.set(key, {
        key,
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

export function findInstallation(
  entry: CatalogEntry,
  installed: InstalledExtension[],
): InstalledExtension | undefined {
  return installed.find(
    (extension) => extension.repository_id === entry.repository.id && extension.tag === entry.tag,
  )
}

export function installAvailability(installation?: InstalledExtension): InstallAvailability {
  const status = installation?.status
  if (!status) return { kind: 'available', label: 'Install' }
  if (status === 'uninstalled') {
    return {
      kind: 'unavailable',
      label: 'Install',
      reason: 'This version was just uninstalled. It can be installed again in a moment.',
    }
  }
  if (RETRYABLE_INSTALL_STATUSES.includes(status)) {
    return {
      kind: 'retry',
      label: 'Retry installation',
      reason: 'The last installation of this version failed.',
    }
  }
  switch (status) {
    case 'installed':
      return {
        kind: 'unavailable',
        label: 'Install',
        reason: 'This version is already installed. Manage it on the Extensions page.',
      }
    case 'uninstalling':
      return {
        kind: 'unavailable',
        label: 'Install',
        reason: 'This version is being uninstalled. Install it again once that has finished.',
      }
    case 'uninstalling_failed':
      return {
        kind: 'unavailable',
        label: 'Install',
        reason:
          'Uninstalling this version failed. Retry the uninstall on the Extensions page first.',
      }
    default:
      return {
        kind: 'unavailable',
        label: 'Install',
        reason: 'This version is being installed. Follow its progress on the Extensions page.',
      }
  }
}
