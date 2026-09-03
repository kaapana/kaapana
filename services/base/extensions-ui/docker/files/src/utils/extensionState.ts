// Pure readers over the kube-helm `/extensions` payload. Extracted from the
// view so the template deals in named states rather than nested lookups; the
// logic is unchanged, including the defensive `?.` chains that keep a row whose
// selected version is missing from `available_versions` from throwing and
// taking the whole table down with it.

/** A multi-installable chart's own catalogue row is never itself a deployment. */
function isCatalogueRow(item: any): boolean {
  return item?.multiinstallable === 'yes' && item?.chart_name === item?.releaseName
}

function deploymentsFor(item: any): any[] {
  return item?.available_versions?.[item?.version]?.deployments ?? []
}

export function checkInstalled(item: any): 'yes' | 'no' {
  if (isCatalogueRow(item)) return 'no'
  return deploymentsFor(item).length > 0 ? 'yes' : 'no'
}

// Returns the backend's `ready` value unchanged, NOT a boolean: call sites
// compare with `=== true`, so coercing here would make a truthy non-`true`
// value (`"True"`, `1`) newly count as ready.
export function checkDeploymentReady(item: any): any {
  if (isCatalogueRow(item)) return false
  const deployments = deploymentsFor(item)
  return deployments.length > 0 ? deployments[0].ready : false
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function getHelmStatus(item: any): string {
  if (isCatalogueRow(item)) return ''
  const deployments = deploymentsFor(item)
  if (deployments.length === 0) return ''
  return capitalize(String(deployments[0].helm_status ?? ''))
}

export function getKubeStatus(item: any): string {
  if (isCatalogueRow(item)) return ''
  const deployments = deploymentsFor(item)
  if (deployments.length === 0) return ''

  const status = deployments[0].kube_status

  if (typeof status === 'string') return status.length > 0 ? capitalize(status) : ''
  if (!Array.isArray(status) || status.length === 0) return ''

  // Above three pods the individual states stop being readable, so summarise
  // them as counts instead of listing every one.
  if (status.length > 3) {
    const counts = new Map<string, number>()
    for (const entry of status) {
      const key = capitalize(String(entry))
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return [...counts].map(([key, count]) => `${key}: ${count}`).join(', ')
  }

  return status.map((entry: any) => capitalize(String(entry))).join(', ')
}

/** A ":8080/path" link is relative to the platform host; anything else is absolute. */
export function getHref(link: string): string {
  return /^:(\d+)(.*)/.test(link) ? `http://${window.location.hostname}${link}` : link
}
