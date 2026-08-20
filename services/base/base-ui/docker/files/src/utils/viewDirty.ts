// Tell the portal-ui shell this view has unsaved in-memory state, so a project
// switch can warn before reloading the iframe.
export function postViewDirty(dirty: boolean): void {
  window.parent.postMessage({ type: 'kaapana:view-dirty', dirty }, window.location.origin)
}
