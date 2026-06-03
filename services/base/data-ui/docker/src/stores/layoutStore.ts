import { defineStore } from 'pinia'

const MIN_COLUMNS = 1
const MAX_COLUMNS = 10
const MIN_TREE_PANEL_WIDTH = 200
const MAX_TREE_PANEL_WIDTH = 480
const DEFAULT_TREE_PANEL_WIDTH = 280
const TREE_WIDTH_STORAGE_KEY = 'data-ui:treePanelWidth'
const TREE_VISIBLE_STORAGE_KEY = 'data-ui:treePanelVisible'

function clamp(value: number): number {
  return Math.min(Math.max(value, MIN_COLUMNS), MAX_COLUMNS)
}

function clampTreeWidth(value: number): number {
  return Math.min(Math.max(value, MIN_TREE_PANEL_WIDTH), MAX_TREE_PANEL_WIDTH)
}

function readPersistedTreeWidth(): number {
  if (typeof window === 'undefined') {
    return DEFAULT_TREE_PANEL_WIDTH
  }
  const raw = window.localStorage.getItem(TREE_WIDTH_STORAGE_KEY)
  if (!raw) {
    return DEFAULT_TREE_PANEL_WIDTH
  }
  const value = Number(raw)
  if (!Number.isFinite(value)) {
    return DEFAULT_TREE_PANEL_WIDTH
  }
  return clampTreeWidth(value)
}

function readPersistedTreeVisible(): boolean {
  if (typeof window === 'undefined') {
    return true
  }
  const raw = window.localStorage.getItem(TREE_VISIBLE_STORAGE_KEY)
  if (raw === null) {
    return true
  }
  return raw === '1' || raw.toLowerCase() === 'true'
}

export const useLayoutStore = defineStore('layout', {
  state: () => ({
    entityDefaultColumns: 1,
    entityCustomColumns: null as number | null,
    treePanelWidth: readPersistedTreeWidth(),
    treePanelVisible: readPersistedTreeVisible(),
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
    setTreePanelWidth(value: number) {
      this.treePanelWidth = clampTreeWidth(value)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(TREE_WIDTH_STORAGE_KEY, String(this.treePanelWidth))
      }
    },
    setTreePanelVisible(value: boolean) {
      this.treePanelVisible = value
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(TREE_VISIBLE_STORAGE_KEY, value ? '1' : '0')
      }
    },
    toggleTreePanel() {
      this.setTreePanelVisible(!this.treePanelVisible)
    },
  },
})
