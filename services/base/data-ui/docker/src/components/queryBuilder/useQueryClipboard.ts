import type { QueryNode } from '@/types/domain'
import { isQueryNodeCandidate } from './utils'

type SnackbarColor = 'success' | 'error'

interface UseQueryClipboardOptions {
  getCurrentQuery: () => QueryNode | null
  applyParsedQuery: (node: QueryNode) => void
  showMessage: (message: string, color: SnackbarColor) => void
}

export function useQueryClipboard(options: UseQueryClipboardOptions) {
  const clipboardSupported = typeof navigator !== 'undefined' && Boolean(navigator.clipboard)

  async function copyQuery() {
    if (!clipboardSupported) {
      options.showMessage('Clipboard API is not available in this browser', 'error')
      return
    }
    const query = options.getCurrentQuery()
    if (!query) {
      options.showMessage('No query to copy yet', 'error')
      return
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(query, null, 2))
      options.showMessage('Copied query JSON to clipboard', 'success')
    } catch (error) {
      console.error(error)
      options.showMessage('Failed to copy query to clipboard', 'error')
    }
  }

  async function pasteQuery() {
    if (!clipboardSupported) {
      options.showMessage('Clipboard API is not available in this browser', 'error')
      return
    }
    try {
      const text = (await navigator.clipboard.readText()).trim()
      if (!text) {
        options.showMessage('Clipboard is empty', 'error')
        return
      }
      const parsed = JSON.parse(text)
      if (!isQueryNodeCandidate(parsed)) {
        options.showMessage('Clipboard content is not a valid query', 'error')
        return
      }
      options.applyParsedQuery(parsed as QueryNode)
      options.showMessage('Pasted query and executed it', 'success')
    } catch (error) {
      console.error(error)
      options.showMessage('Failed to read query from clipboard', 'error')
    }
  }

  return {
    clipboardSupported,
    copyQuery,
    pasteQuery,
  }
}
