import { defineStore } from 'pinia'

export const useDatasetsStore = defineStore('datasets', {
  state: () => ({
    activeTags: [] as string[],
    multiSelectKeyPressed: false,
    selectedItems: [] as string[],
    detailViewItem: null as string | null,
    validationResultItem: null as string | null,
    showValidationResults: false,
  }),
  actions: {
    setActiveTags(activeTags: string[]) {
      this.activeTags = activeTags
    },
    setMultiSelectKeyPressed(multiSelectKeyPressed: boolean) {
      this.multiSelectKeyPressed = multiSelectKeyPressed
    },
    setSelectedItems(selectedItems: string[]) {
      this.selectedItems = selectedItems
    },
    setDetailViewItem(detailViewItem: string | null) {
      this.detailViewItem = detailViewItem
    },
    setValidationResultItem(validationResultItem: string | null) {
      this.validationResultItem = validationResultItem
    },
    setShowValidationResults(showValidationResults: boolean) {
      this.showValidationResults = showValidationResults
    },
    resetDetailViewItem() {
      this.detailViewItem = null
    },
  },
})
