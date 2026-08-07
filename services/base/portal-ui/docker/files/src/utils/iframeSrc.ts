import type { RouteLocationNormalizedGeneric } from 'vue-router'
import { useMenuStore } from '@/stores/menu'
import type { MenuEntry } from '@/types/menu'

// The route fields the iframe src depends on; satisfied both by useRoute()
// (IframeHost) and by the `to`/`from` locations in a router guard, which lets
// the guard predict whether a navigation would reload the iframe.
export type RouteView = Pick<RouteLocationNormalizedGeneric, 'name' | 'params' | 'query'>

// /help has no menu entry: docs are gateway-whitelisted for every role, while
// the "Documentation" menu entry is only visible to roles with /docs access.
export const HELP_ENTRY: MenuEntry = {
  type: 'entry',
  id: 'help',
  label: 'Help',
  icon: 'mdi-help-circle',
  path: '/docs/faq_root.html',
  target: 'iframe',
  project: 'none',
  default: false,
  order: 0,
}

/** Menu entry (plus leftover path segments) a shell route displays. */
export function resolveViewEntry(route: RouteView): { entry: MenuEntry; rest: string[] } | null {
  const menu = useMenuStore()
  if (route.name === 'view') {
    const segments = ([] as string[]).concat((route.params.segments as string[]) || [])
    return menu.resolvePath(segments)
  }
  if (route.name === 'help') return { entry: HELP_ENTRY, rest: [] }
  return menu.defaultEntry ? { entry: menu.defaultEntry, rest: [] } : null
}

/** The iframe src a shell route renders, given the project slug in scope. */
export function iframeSrcFor(route: RouteView, slug: string | null): string {
  const resolved = resolveViewEntry(route)
  if (!resolved) return ''
  const path = resolved.entry.path
  const rest = resolved.rest.join('/')
  const query = new URLSearchParams(route.query as Record<string, string>).toString()
  // Without a rest segment the configured path is used VERBATIM: Airflow 404s
  // on /flow/home/, while /docs/ and /dcm4chee-arc/ui2/ break without the
  // trailing slash (ingress miss or a mixed-content directory redirect).
  const base = rest ? path.replace(/\/$/, '') + '/' + rest : path
  // "path"-scoped views get the project in their document URL; recomputing on
  // a project switch reloads the iframe with the new scope.
  const prefix = resolved.entry.project === 'path' && slug ? `/project/${slug}` : ''
  return `${prefix}${base}${query ? '?' + query : ''}`
}
