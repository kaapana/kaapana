import type { Confirmation } from '@/composables/useConfirmation'
import type { ProjectItem } from '@/common/types'

type Named = Pick<ProjectItem, 'name'>

export function deleteProjectConfirmation(project: Named, action: () => unknown): Confirmation {
  return {
    color: 'error',
    title: `Delete "${project.name}"?`,
    text:
      'Deletes the project with its members, settings and files. DICOM data that no other ' +
      "project holds is permanently deleted from the platform, including the admin project's " +
      'copy. This cannot be undone; to keep the data, archive it instead.',
    confirmText: 'Delete project',
    action,
  }
}

export function archiveProjectConfirmation(project: Named, action: () => unknown): Confirmation {
  return {
    color: 'primary',
    title: `Archive "${project.name}"?`,
    text:
      'The project becomes read-only: no uploads, no data deletion, no changes to members or ' +
      'workflows. Its data stays accessible and can still be transferred or downloaded. Let ' +
      'running workflows finish first. You can unarchive the project at any time.',
    confirmText: 'Archive project',
    action,
  }
}
