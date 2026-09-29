import { watch } from 'vue'

/** At a dialog's after-leave Vuetify has only hidden its content (v-show), and
 *  activeElement can still point into it. */
export function hasVisibleFocus(): boolean {
  const active = document.activeElement
  if (!active || active === document.body || !active.isConnected) return false
  return active.getClientRects().length > 0
}

/**
 * Vuetify returns focus only to a dialog's activator, never for a v-model dialog.
 * restoreFocus skips while focus is visible, so a dialog opening another keeps it.
 */
export function useFocusReturn(open: () => boolean) {
  let opener: HTMLElement | null = null

  watch(
    open,
    (isOpen) => {
      if (isOpen) {
        opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
      }
    },
    { immediate: true },
  )

  function restoreFocus() {
    if (hasVisibleFocus()) return
    const target = opener
    opener = null
    if (target?.isConnected) target.focus()
  }

  return { restoreFocus }
}
