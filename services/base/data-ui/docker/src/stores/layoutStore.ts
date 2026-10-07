import { defineStore } from 'pinia'

const MIN_COLUMNS = 1
const MAX_COLUMNS = 10

function clamp(value: number): number {
  return Math.min(Math.max(value, MIN_COLUMNS), MAX_COLUMNS)
}

export const useLayoutStore = defineStore('layout', {
  state: () => ({
    entityDefaultColumns: 1,
    entityCustomColumns: null as number | null,
  }),
  getters: {
    effectiveEntityColumns(state): number {
      return state.entityCustomColumns ?? state.entityDefaultColumns
    },
    canZoomEntityOut(state): boolean {
      return (state.entityCustomColumns ?? state.entityDefaultColumns) > MIN_COLUMNS
    },
    canZoomEntityIn(state): boolean {
      return (state.entityCustomColumns ?? state.entityDefaultColumns) < MAX_COLUMNS
    },
    hasCustomEntityColumns(state): boolean {
      return state.entityCustomColumns !== null
    },
  },
  actions: {
    setEntityDefaultColumns(value: number) {
      this.entityDefaultColumns = clamp(value)
      if (this.entityCustomColumns !== null) {
        this.entityCustomColumns = clamp(this.entityCustomColumns)
      }
    },
    setEntityCustomColumns(value: number | null) {
      if (value === null) {
        this.entityCustomColumns = null
        return
      }
      const clamped = clamp(value)
      this.entityCustomColumns = clamped === this.entityDefaultColumns ? null : clamped
    },
    zoomEntities(delta: number) {
      const current = this.entityCustomColumns ?? this.entityDefaultColumns
      const next = clamp(current + delta)
      this.setEntityCustomColumns(next)
    },
    resetEntityColumns() {
      this.entityCustomColumns = null
    },
  },
})
