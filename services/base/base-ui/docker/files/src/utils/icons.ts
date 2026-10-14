// Semantic action to MDI icon name.
//
// Icon *delivery* is already uniform across the platform — @mdi/font with
// vuetify/iconsets/mdi everywhere — so this fixes only icon *choice*, where the
// same action was drawn with different symbols in different views: `delete`
// alone appeared as four different names.
//
// Each name below is the one already most used for that action across the
// inspected frontends, so adopting the map changes the fewest call sites rather
// than imposing a preference. Reference the map, never an 'mdi-*' string, so
// that changing the symbol for an action is one edit instead of a search.
//
// The set is expected to grow as more actions are named. It is deliberately not
// a catalogue of every icon in use — only of actions whose meaning should be
// constant across views.
export const kaapanaIcons = {
  account: 'mdi-account-circle',
  add: 'mdi-plus',
  apiDocs: 'mdi-api',
  close: 'mdi-close',
  confirm: 'mdi-check',
  copy: 'mdi-content-copy',
  delete: 'mdi-delete',
  download: 'mdi-download',
  edit: 'mdi-pencil',
  error: 'mdi-alert-circle',
  expand: 'mdi-chevron-down',
  externalLink: 'mdi-open-in-new',
  help: 'mdi-help-circle-outline',
  info: 'mdi-information',
  logout: 'mdi-exit-to-app',
  more: 'mdi-dots-vertical',
  notifications: 'mdi-bell-outline',
  notificationsUnread: 'mdi-bell-ring',
  preview: 'mdi-eye',
  refresh: 'mdi-refresh',
  restart: 'mdi-restart',
  save: 'mdi-content-save',
  search: 'mdi-magnify',
  settings: 'mdi-cog',
  sidebar: 'mdi-dock-left',
  start: 'mdi-play',
  stop: 'mdi-stop-circle-outline',
  success: 'mdi-check-circle',
  // Not `error` (mdi-alert-circle): a warning must not look like an error.
  warning: 'mdi-alert',
} as const

export type KaapanaIconName = keyof typeof kaapanaIcons
