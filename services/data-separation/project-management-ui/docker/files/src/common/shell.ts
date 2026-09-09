// Ask the portal-ui shell to re-read its project list after a mutation here, so
// the sidebar does not show a stale set until its next poll. The wire contract
// is documented in docs/source/development_guide/preview/landing_page_integration.rst.
export function refreshShell(): void {
    if (window.parent !== window) {
        window.parent.postMessage({ type: 'kaapana:shell-refresh' }, window.location.origin);
    }
}
