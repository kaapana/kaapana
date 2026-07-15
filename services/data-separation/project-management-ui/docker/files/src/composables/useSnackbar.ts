import { ref } from 'vue'

export function useSnackbar() {
  const showSnackbar = ref(false)
  const snackbarText = ref('')
  const snackbarColor = ref('info')

  function notify(text: string, color: 'success' | 'error' | 'info' | 'warning' = 'info') {
    snackbarText.value = text
    snackbarColor.value = color
    showSnackbar.value = true
  }

  return { showSnackbar, snackbarText, snackbarColor, notify }
}
