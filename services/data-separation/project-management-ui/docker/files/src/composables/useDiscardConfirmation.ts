import { ref } from 'vue'
import { hasUnsavedChanges } from '@/composables/useViewDirty'

// Module-level so the one dialog in App.vue answers confirmDiscard() from any page.
const open = ref(false)
let settle: ((discard: boolean) => void) | null = null

/** Resolves true when nothing is unsaved or the user chose to discard it. */
export function confirmDiscard(): Promise<boolean> {
  if (!hasUnsavedChanges()) return Promise.resolve(true)
  open.value = true
  return new Promise((resolve) => (settle = resolve))
}

export function useDiscardDialog() {
  function answer(discard: boolean) {
    settle?.(discard)
    settle = null
  }
  return { open, answer }
}
