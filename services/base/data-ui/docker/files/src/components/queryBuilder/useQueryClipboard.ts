import type { QueryNode } from '@/types/domain'
import { isQueryNodeCandidate } from './utils'

type MessageColor = 'success' | 'error'

interface UseQueryClipboardOptions {
  getCurrentQuery: () => QueryNode | null
  applyParsedQuery: (node: QueryNode) => void
  showMessage: (title: string, text: string, color: MessageColor) => void
}

export function useQueryClipboard(options: UseQueryClipboardOptions) {
  const clipboardSupported = typeof navigator !== 'undefined' && Boolean(navigator.clipboard)

  async function copyQuery() {
    if (!clipboardSupported) {
      options.showMessage(
        'Clipboard not available',
        'The browser does not allow access to the clipboard.',
        'error',
      )
      return
    }
    const query = options.getCurrentQuery()
    if (!query) {
      options.showMessage('Nothing to copy', 'Add a condition to the filter first.', 'error')
      return
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(query, null, 2))
      options.showMessage(
        'Filter copied',
        'The filter was copied to the clipboard as JSON.',
        'success',
      )
    } catch {
      options.showMessage(
        'Filter not copied',
        'The browser did not allow copying to the clipboard.',
        'error',
      )
    }
  }

  async function pasteQuery() {
    if (!clipboardSupported) {
      options.showMessage(
        'Clipboard not available',
        'The browser does not allow access to the clipboard.',
        'error',
      )
      return
    }
    try {
      const text = (await navigator.clipboard.readText()).trim()
      if (!text) {
        options.showMessage('Nothing to paste', 'The clipboard is empty.', 'error')
        return
      }
      const parsed = JSON.parse(text)
      if (!isQueryNodeCandidate(parsed)) {
        options.showMessage(
          'Filter not pasted',
          'The clipboard does not hold a filter. Copy a filter as JSON first.',
          'error',
        )
        return
      }
      options.applyParsedQuery(parsed as QueryNode)
      options.showMessage('Filter pasted', 'The pasted filter was applied.', 'success')
    } catch {
      options.showMessage(
        'Filter not pasted',
        'The clipboard could not be read or does not hold valid JSON.',
        'error',
      )
    }
  }

  return {
    clipboardSupported,
    copyQuery,
    pasteQuery,
  }
}
