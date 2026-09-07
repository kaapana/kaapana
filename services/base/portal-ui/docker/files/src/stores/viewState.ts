import { defineStore } from 'pinia'

// Module-level: a resolver function is not state worth tracking.
let pendingResolve: ((leave: boolean) => void) | null = null

// Unsaved in-memory state of the embedded view, reported via the
// kaapana:view-dirty postMessage (handled in App.vue); confirmLeave() gates
// state-destroying actions.
export const useViewStateStore = defineStore('viewState', {
  state: () => ({
    dirty: false,
    // Drives the shell-level "Unsaved changes" dialog (UnsavedChangesDialog).
    confirmVisible: false,
  }),
  actions: {
    setDirty(dirty: boolean) {
      this.dirty = dirty
      // Dirty going away makes an open confirm moot — dismiss it as "stay" so
      // it cannot linger and act on state that no longer exists.
      if (!dirty) this.resolveLeave(false)
    },
    /**
     * Gate for actions that would discard the embedded view's state. Resolves
     * true when leaving is OK: immediately for a clean view, otherwise once the
     * user picks "Leave view" in the shell dialog ("Stay" resolves false).
     */
    confirmLeave(): Promise<boolean> {
      if (!this.dirty) return Promise.resolve(true)
      // A second request while one is pending supersedes it: the first caller
      // is told to stay (vue-router cancels its navigation anyway).
      pendingResolve?.(false)
      return new Promise((resolve) => {
        pendingResolve = resolve
        this.confirmVisible = true
      })
    },
    resolveLeave(leave: boolean) {
      this.confirmVisible = false
      pendingResolve?.(leave)
      pendingResolve = null
    },
  },
})
