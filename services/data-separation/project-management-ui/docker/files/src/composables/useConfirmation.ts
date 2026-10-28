import { ref } from 'vue'

export interface Confirmation {
  title: string
  text: string
  confirmText: string
  // error: destructive; primary: reversible but high-impact.
  color: 'error' | 'primary'
  action: () => unknown
}

export function useConfirmation() {
  const confirmOpen = ref(false)
  // Kept after the dialog closes so its content does not blank out during the
  // leave transition; the next ask replaces it.
  const confirmation = ref<Confirmation>({
    title: '',
    text: '',
    confirmText: 'Confirm',
    color: 'primary',
    action: () => undefined,
  })

  function ask(next: Confirmation) {
    confirmation.value = next
    confirmOpen.value = true
  }

  function runConfirmed() {
    confirmation.value.action()
  }

  return { confirmOpen, confirmation, ask, runConfirmed }
}
