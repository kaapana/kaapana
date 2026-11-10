import type {
  CatalogEntry,
  CatalogEntryGroup,
  CatalogFilters,
  InstallAvailability,
  UpdateConfirmation,
} from '@/features/catalog/types'
import type { ExtensionStatus, InstalledExtension } from '@/shared/types/apiSchemas'
import { isTransitional, plural, RETRYABLE_INSTALL_STATUSES } from '@/shared/utils/status'

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
  return `${entry.repository.id}:${entry.manifest.id}`
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

  return Array.from(groups.values()).map((group) => {
    const entries = sortEntriesByVersion(group.entries)
    return { ...group, manifestName: entries[0]!.manifest.name, entries }
  })
}

function compareVersions(left: string, right: string): number {
  return left.localeCompare(right, undefined, { numeric: true, sensitivity: 'base' })
}

function sortEntriesByVersion(entries: CatalogEntry[]): CatalogEntry[] {
  return [...entries].sort((leftEntry, rightEntry) =>
    compareVersions(rightEntry.manifest.version, leftEntry.manifest.version),
  )
}

export function findInstallation(
  entry: CatalogEntry,
  installed: InstalledExtension[],
): InstalledExtension | undefined {
  return (
    installed.find(
      (extension) =>
        extension.manifest.id === entry.manifest.id && extension.status !== 'uninstalled',
    ) ??
    installed.find(
      (extension) => extension.repository_id === entry.repository.id && extension.tag === entry.tag,
    )
  )
}

export function installAvailability(
  entry: CatalogEntry,
  installation?: InstalledExtension,
): InstallAvailability {
  if (!installation) return { kind: 'available', label: 'Install' }
  if (installation.repository_id === entry.repository.id && installation.tag === entry.tag) {
    return sameVersionAvailability(installation.status)
  }
  return otherVersionAvailability(entry, installation)
}

function otherVersionAvailability(
  entry: CatalogEntry,
  installation: InstalledExtension,
): InstallAvailability {
  const installedVersion = installation.manifest.version
  if (!installation.repository_id) {
    return {
      kind: 'unavailable',
      label: 'Install',
      reason: `Version ${installedVersion} is installed from the removed repository ${installation.repository_name}. Uninstall it first.`,
    }
  }
  if (installation.repository_id !== entry.repository.id) {
    return {
      kind: 'unavailable',
      label: 'Install',
      reason: `Version ${installedVersion} is installed from another repository. Newer versions must come from that repository.`,
    }
  }
  if (installation.status !== 'installed' && installation.status !== 'update_failed') {
    return {
      kind: 'unavailable',
      label: 'Install',
      reason: isTransitional(installation.status)
        ? `Version ${installedVersion} is being processed. Try again once that has finished.`
        : `Version ${installedVersion} did not finish installing. Retry or uninstall it first.`,
    }
  }
  const comparison = compareVersions(entry.manifest.version, installedVersion)
  if (comparison === 0) {
    return { kind: 'unavailable', label: 'Install', reason: 'This version is already installed.' }
  }
  if (comparison < 0) {
    return {
      kind: 'unavailable',
      label: 'Install',
      reason: `Version ${installedVersion} is installed. Downgrades are not supported.`,
    }
  }
  const failedVersion =
    installation.status === 'update_failed'
      ? installation.pending_update?.manifest.version
      : undefined
  if (failedVersion !== undefined) {
    const failedComparison = compareVersions(entry.manifest.version, failedVersion)
    if (failedComparison === 0) {
      return {
        kind: 'update',
        label: 'Retry update',
        reason: `The update to this version failed. Version ${installedVersion} is still installed.`,
      }
    }
    if (failedComparison < 0) {
      return {
        kind: 'update',
        label: `Update to ${entry.manifest.version}`,
        reason: `The update to ${failedVersion} failed. Version ${installedVersion} is still installed.`,
        confirm: belowFailedTargetConfirmation(entry, installation, failedVersion),
      }
    }
  }
  return {
    kind: 'update',
    label: `Update to ${entry.manifest.version}`,
    reason: `Version ${installedVersion} is installed.`,
  }
}

function belowFailedTargetConfirmation(
  entry: CatalogEntry,
  installation: InstalledExtension,
  failedVersion: string,
): UpdateConfirmation {
  const reached = installation.contents
    .filter((content) => content.applied_version === failedVersion)
    .map((content) => content.name)
  const back = reached.length
    ? `${plural(reached.length, 'item')} already on ${failedVersion} (${reached.join(', ')}) will be set back to ${entry.manifest.version}.`
    : `No item reached ${failedVersion}.`
  return {
    title: `Update "${entry.manifest.name}" to ${entry.manifest.version}?`,
    text: `The update to ${failedVersion} failed, and ${entry.manifest.version} is older than that. ${back}`,
  }
}

function sameVersionAvailability(status: ExtensionStatus): InstallAvailability {
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
    case 'updating':
      return {
        kind: 'unavailable',
        label: 'Install',
        reason: 'This version is being updated. Follow its progress on the Extensions page.',
      }
    case 'update_failed':
      return {
        kind: 'unavailable',
        label: 'Install',
        reason:
          'This version is installed, but its update failed. Retry the update from the newer version.',
      }
    default:
      return {
        kind: 'unavailable',
        label: 'Install',
        reason: 'This version is being installed. Follow its progress on the Extensions page.',
      }
  }
}
