import { kaapanaIcons } from '@kaapana/base-ui'

export { kaapanaIcons }

export const galleryIcons = {
  dataset: 'mdi-folder',
  datasetEdit: 'mdi-folder-edit-outline',
  datasetAdd: 'mdi-folder-plus-outline',
  datasetRemove: 'mdi-folder-minus-outline',
  download: 'mdi-download-circle',
  downloadFile: 'mdi-file-download',
  more: 'mdi-dots-vertical',
  filterAdd: 'mdi-filter-plus-outline',
  showFilters: 'mdi-filter-menu',
  hideFilters: 'mdi-filter-menu-outline',
  copy: 'mdi-content-copy',
  inputList: 'mdi-form-dropdown',
  inputFreeText: 'mdi-form-textarea',
  tag: 'mdi-tag-outline',
  preview: 'mdi-eye',
  // Not the shared `error` icon (mdi-alert-circle): a warning must not look like an error.
  warning: 'mdi-alert',
  incomplete: 'mdi-format-page-break',
} as const
