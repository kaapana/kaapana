import type { Dataset } from '@/types'

export function datasetLabel(item: Dataset) {
  return `${item.name} (${item.access_level})`
}

export function datasetListNoDataText(
  list: { loading: boolean; failed: boolean; count: number; search?: string | null },
  noneYet: string,
) {
  if (list.loading && list.count === 0) return 'Loading datasets…'
  if (list.failed) return 'The datasets could not be loaded. Reopen this list to try again.'
  if (list.count > 0) return `No dataset matches “${list.search ?? ''}”.`
  return noneYet
}

/** A dataset is identified by its name and access level together. */
export function sameDataset(a: Dataset | null | undefined, b: Dataset | null | undefined) {
  return !!a && !!b && a.name === b.name && a.access_level === b.access_level
}
