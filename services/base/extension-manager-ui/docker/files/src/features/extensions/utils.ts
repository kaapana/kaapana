import type { InstalledExtension, Repository } from '@/shared/types/apiSchemas'
import { REMOVED_REPOSITORY, UPLOADED_FILE } from '@/shared/utils/status'

export function extensionSourceName(
  extension: InstalledExtension,
  repository: Repository | null | undefined,
): string {
  if (extension.origin === 'upload') return UPLOADED_FILE
  if (repository) return repository.name
  return extension.repository_id ?? REMOVED_REPOSITORY
}
