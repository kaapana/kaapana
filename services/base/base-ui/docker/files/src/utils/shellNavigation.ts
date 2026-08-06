/**
 * Ask the portal-ui shell to open another view. `path` is a shell route as the
 * menu addresses it: `/web/<section>/<id>`, or `/web/-/<id>` for a top-level
 * entry. Embedded, the shell resolves it (running its view-dirty confirm
 * first); standalone, navigate this document directly.
 */
export function navigateShell(path: string): void {
  if (window.parent !== window) {
    window.parent.postMessage({ type: 'kaapana:navigate', path }, window.location.origin)
    return
  }
  window.top!.location.href = path
}
