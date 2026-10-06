import { useEntityStore } from '@/stores/entityStore'
import type { MetadataEntry } from '@/types/domain'
import { notifyFailure, notifySuccess } from '@/utils/notify'

export async function saveMetadataEntry(
  entityId: string,
  entry: MetadataEntry,
  created: boolean,
): Promise<boolean> {
  try {
    await useEntityStore().saveMetadataEntry(entityId, entry)
    notifySuccess(
      created ? 'Metadata entry added' : 'Metadata entry saved',
      `The entry "${entry.key}" was ${created ? 'added' : 'saved'}.`,
    )
    return true
  } catch (error) {
    notifyFailure(
      created ? 'Metadata entry not added' : 'Metadata entry not saved',
      `The entry "${entry.key}" could not be ${created ? 'added' : 'saved'}.`,
      error,
    )
    return false
  }
}

export async function removeMetadataEntry(entityId: string, key: string): Promise<boolean> {
  try {
    await useEntityStore().deleteMetadataEntry(entityId, key)
    notifySuccess('Metadata entry removed', `The entry "${key}" was removed.`)
    return true
  } catch (error) {
    notifyFailure('Metadata entry not removed', `The entry "${key}" could not be removed.`, error)
    return false
  }
}
