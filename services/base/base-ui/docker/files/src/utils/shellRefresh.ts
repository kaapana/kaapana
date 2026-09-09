/**
 * Ask the portal-ui shell to re-read what it shows about the platform — its
 * menu and the user's project list — after this view changed something there.
 * Standalone this does nothing: there is no shell menu to refresh, and
 * reloading the document would discard the view's just-submitted state.
 */
export function refreshShell(): void {
  if (window.parent !== window) {
    window.parent.postMessage({ type: 'kaapana:shell-refresh' }, window.location.origin)
  }
}
