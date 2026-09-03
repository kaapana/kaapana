import { kaapanaIcons } from '@kaapana/base-ui'

// Actions whose meaning is constant across the platform come from the shared
// map — never an 'mdi-*' string at the call site (design guidelines, "Icons").
export { kaapanaIcons }

// Icons for this view's own domain vocabulary. The shared map is deliberately
// not a catalogue of every symbol in use, so these stay local; they are named
// here rather than inline so one edit changes every occurrence.
export const galleryIcons = {
  dataset: 'mdi-folder',
  datasetEdit: 'mdi-folder-edit-outline',
  datasetAdd: 'mdi-folder-plus-outline',
  datasetRemove: 'mdi-folder-minus-outline',
  download: 'mdi-download-circle',
  downloadFile: 'mdi-file-download',
  more: 'mdi-dots-vertical',
  filterAdd: 'mdi-filter-plus-outline',
  filtersShown: 'mdi-filter-menu',
  filtersHidden: 'mdi-filter-menu-outline',
  copy: 'mdi-content-copy',
  inputList: 'mdi-form-dropdown',
  inputFreeText: 'mdi-form-textarea',
  tag: 'mdi-tag-outline',
  preview: 'mdi-eye',
  // `error` in the shared map is mdi-alert-circle; a warning must not be drawn
  // with the error symbol, so the two stay visually distinct here.
  warning: 'mdi-alert',
  incomplete: 'mdi-format-page-break',
} as const
