import { kaapanaIcons } from '@kaapana/base-ui'

// Platform-wide actions use the shared icon map from base-ui.
export { kaapanaIcons }

// Icons for this view's own vocabulary.
export const projectIcons = {
  archive: 'mdi-archive-arrow-down',
  unarchive: 'mdi-archive-arrow-up',
  back: 'mdi-arrow-left',
  open: 'mdi-arrow-right',
  collapse: 'mdi-chevron-up',
  roleRights: 'mdi-shield-key',
  reset: 'mdi-restore',
  addUser: 'mdi-account-plus',
  editRole: 'mdi-account-edit',
  searchUser: 'mdi-account-search-outline',
  systemUsers: 'mdi-account-cog',
  workflow: 'mdi-gamepad-variant',
  application: 'mdi-application-outline',
} as const

export const roleIcons: Record<string, string> = {
  admin: 'mdi-shield-crown',
  'principal-investigator': 'mdi-shield-account',
  scientist: 'mdi-flask-outline',
}
