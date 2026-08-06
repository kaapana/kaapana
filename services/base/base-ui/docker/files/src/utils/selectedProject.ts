// The shell serves every view under /project/<short_id>/<view>/ and reloads
// the iframe on a project switch, so the document URL is the single source of
// the selected project. Served without the prefix (standalone), the selection
// is empty.
export function getProjectSlug(): string | null {
  return window.location.pathname.match(/^\/project\/([^/]+)\//)?.[1] ?? null
}

/** '/project/<short_id>' document prefix, or '' when served unscoped. */
export function getProjectBase(): string {
  const slug = getProjectSlug()
  return slug ? `/project/${slug}` : ''
}

/**
 * Ask the shell to switch the platform to another project. Embedded, this
 * posts to the shell (so its view-dirty guard still runs); standalone, it
 * navigates this document under the new prefix.
 */
export function switchProject(slug: string): void {
  if (window.parent !== window) {
    window.parent.postMessage({ type: 'kaapana:project-switch', slug }, window.location.origin)
    return
  }
  window.location.href = `/project/${slug}`
}
