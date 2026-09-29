import type { Dataset } from '@/types'

export function datasetLabel(item: Dataset) {
  return `${item.name} (${item.access_level})`
}

/** A dataset is identified by its name and access level together. */
export function sameDataset(a: Dataset | null | undefined, b: Dataset | null | undefined) {
  return !!a && !!b && a.name === b.name && a.access_level === b.access_level
}
