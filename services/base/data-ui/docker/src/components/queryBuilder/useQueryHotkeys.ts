import { onBeforeUnmount, onMounted } from 'vue'
import { shouldIgnoreHotkeyTarget } from './utils'

interface QueryHotkeyHandlers {
  focusBuilder: () => void
  copyQuery: () => void
  pasteQuery: () => void
  resetQuery: () => void
  canReset: () => boolean
}

export function useQueryHotkeys(handlers: QueryHotkeyHandlers) {
  function handleKey(event: KeyboardEvent) {
    if (event.defaultPrevented || shouldIgnoreHotkeyTarget(event.target)) {
      return
    }
    const lowerKey = event.key.toLowerCase()
    const simpleModifier = event.metaKey || event.ctrlKey || event.altKey

    if (!simpleModifier && lowerKey === 'f') {
      event.preventDefault()
      handlers.focusBuilder()
      return
    }

    if (!simpleModifier && lowerKey === 'c') {
      event.preventDefault()
      handlers.copyQuery()
      return
    }

    if (!simpleModifier && lowerKey === 'p') {
      event.preventDefault()
      handlers.pasteQuery()
      return
    }

    if (!simpleModifier && lowerKey === 'x') {
      if (!handlers.canReset()) {
        return
      }
      event.preventDefault()
      handlers.resetQuery()
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKey)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKey)
  })
}
