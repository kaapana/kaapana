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
  add: 'mdi-plus',
  close: 'mdi-close',
  confirm: 'mdi-check',
  delete: 'mdi-delete',
  edit: 'mdi-pencil',
  error: 'mdi-alert-circle',
  expand: 'mdi-chevron-down',
  externalLink: 'mdi-open-in-new',
  help: 'mdi-help-circle-outline',
  info: 'mdi-information',
  refresh: 'mdi-refresh',
  save: 'mdi-content-save',
  search: 'mdi-magnify',
  start: 'mdi-play',
  success: 'mdi-check-circle',
} as const

export type KaapanaIconName = keyof typeof kaapanaIcons
