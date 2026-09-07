// Wire contract of GET /portal-api/menu — keep in sync with portal-api.
export interface DevLink {
  label: string
  /** Absolute path of a service's API docs, e.g. "/kaapana-backend/docs" */
  path: string
}

export interface MenuEntry {
  type: 'entry'
  /** Stable route slug used in /:section/:entry (or /:entry for top-level) */
  id: string
  label: string
  icon: string
  /** Iframe src prefix (same-origin ingress path), e.g. "/data-gallery-ui/" */
  path: string
  /** "iframe" renders inside the shell, "tab" opens a new browser tab */
  target: 'iframe' | 'tab'
  /**
   * How the view consumes the selected project (kaapana.ai/ui.project):
   * "path"  — iframe src is prefixed with /project/<short_id>; the shell
   *           reloads the iframe when the project changes.
   * "none"  — project-agnostic.
   */
  project: 'path' | 'none'
  /** The default entry is shown at "/" */
  default: boolean
  order: number
  /**
   * Absolute path (kaapana.ai/ui.badge-path) the shell polls for a count badge
   * on this entry; the response is {count:number}. Absent/empty means no badge.
   */
  badgePath?: string
  /**
   * API docs of the services behind this entry (kaapana.ai/ui.dev-links),
   * offered in dev mode. They point at other ingresses than `path`, so each is
   * authorized on its own. Absent/empty means none.
   */
  devLinks?: DevLink[]
}

export interface MenuSection {
  type: 'section'
  id: string
  label: string
  icon: string
  order: number
  entries: MenuEntry[]
}

export type MenuItem = MenuSection | MenuEntry

export interface MenuResponse {
  /** Pre-sorted by the backend; sections and top-level entries interleaved */
  items: MenuItem[]
}
