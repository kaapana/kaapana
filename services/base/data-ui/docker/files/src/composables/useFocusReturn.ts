import { watch, type Ref } from 'vue'

export function useFocusReturn(open: Ref<boolean>) {
  let opener: HTMLElement | null = null

  watch(open, (value) => {
    if (value) {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    }
  })

  return function restoreFocus() {
    if (!open.value) {
      opener?.focus()
      opener = null
    }
  }
}
