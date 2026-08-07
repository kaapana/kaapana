import { defineStore } from 'pinia'
import http from '@/api/http'
import { fetchMenu } from '@/api/menu'
import { fetchPolicyData } from '@/api/auth'
import { checkAuthR, type PolicyData } from '@/utils/opa'
import type { DevLink, MenuEntry, MenuItem, MenuSection } from '@/types/menu'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'

/** Route param used as section slug for top-level (section-less) entries. */
export const NO_SECTION = '-'

/** Backend caches ingress discovery for 10s; polling slightly slower than that. */
const POLL_INTERVAL_MS = 15_000

export const useMenuStore = defineStore('menu', {
  state: () => ({
    items: [] as MenuItem[],
    policyData: null as PolicyData | null,
    loaded: false,
    // Last refresh failed, so the drawer can tell "backend unreachable" apart
    // from "nothing to show". Set in refresh() because the poll swallows rejections.
    error: false,
    pollTimer: null as ReturnType<typeof setInterval> | null,
    // Badge counts for entries declaring a badgePath, keyed by entry.path
    // (unique per ingress).
    badgeCounts: {} as Record<string, number>,
  }),
  getters: {
    // Entry visible iff the user's roles authorize its ingress path;
    // section visible iff any of its entries is visible.
    isEntryVisible(): (entry: MenuEntry) => boolean {
      const auth = useAuthStore()
      return (entry) => {
        if (!this.policyData || !auth.user) return false
        return checkAuthR(this.policyData, entry.path, auth.user)
      }
    },
    /**
     * Dev links of an entry the user's roles authorize. They address other
     * services' ingresses than entry.path, so isEntryVisible does not cover
     * them and each one is checked on its own.
     */
    visibleDevLinks(): (entry: MenuEntry) => DevLink[] {
      const auth = useAuthStore()
      return (entry) => {
        const policyData = this.policyData
        const user = auth.user
        if (!policyData || !user) return []
        return (entry.devLinks ?? []).filter((link) => checkAuthR(policyData, link.path, user))
      }
    },
    visibleItems(): MenuItem[] {
      return this.items
        .map((item) => {
          if (item.type === 'entry') {
            return this.isEntryVisible(item) ? item : null
          }
          const entries = item.entries.filter((entry) => this.isEntryVisible(entry))
          return entries.length > 0 ? ({ ...item, entries } as MenuSection) : null
        })
        .filter((item): item is MenuItem => item !== null)
    },
    /** Entry shown at "/" — the backend flags exactly one entry as default. */
    defaultEntry(): MenuEntry | null {
      for (const item of this.items) {
        if (item.type === 'entry' && item.default) return item
        if (item.type === 'section') {
          const entry = item.entries.find((e) => e.default)
          if (entry) return entry
        }
      }
      return null
    },
    /**
     * Resolve URL path segments to a menu entry plus the leftover segments
     * forwarded to the iframe: /<section>/<entry>/<rest…> for sectioned
     * entries, /<entry>/<rest…> for top-level ones.
     */
    resolvePath(): (segments: string[]) => { entry: MenuEntry; rest: string[] } | null {
      return (segments) => {
        const [first, second] = segments
        if (!first) return null
        for (const item of this.items) {
          if (item.type === 'entry' && item.id === first) {
            return { entry: item, rest: segments.slice(1) }
          }
          if (item.type === 'section' && item.id === first) {
            const entry = second ? (item.entries.find((e) => e.id === second) ?? null) : null
            return entry ? { entry, rest: segments.slice(2) } : null
          }
        }
        return null
      }
    },
    /** Badge count for an entry (0 when it has none or hasn't been polled). */
    badgeCount(): (entry: MenuEntry) => number {
      return (entry) => this.badgeCounts[entry.path] ?? 0
    },
    /** Section slug an entry lives under, NO_SECTION for top-level entries. */
    sectionOf(): (entry: MenuEntry) => string {
      return (entry) => {
        for (const item of this.items) {
          if (item.type === 'section' && item.entries.some((e) => e.id === entry.id)) {
            return item.id
          }
        }
        return NO_SECTION
      }
    },
  },
  actions: {
    async ensureLoaded() {
      if (this.loaded) return
      await this.refresh()
      this.loaded = true
    },
    async refresh() {
      const [menu, policyData] = await Promise.all([fetchMenu(), fetchPolicyData()]).catch(
        (err) => {
          this.error = true
          throw err
        },
      )
      this.error = false
      // Reassign only on change so polling doesn't churn the drawer.
      if (JSON.stringify(menu.items) !== JSON.stringify(this.items)) {
        this.items = menu.items
      }
      if (JSON.stringify(policyData) !== JSON.stringify(this.policyData)) {
        this.policyData = policyData
      }
      await this.refreshBadges()
    },
    /**
     * Poll each entry's badgePath into badgeCounts. The http interceptor scopes
     * by the document URL, so this must run after it reflects the selected
     * project. Never throws — a failed fetch keeps the last known count.
     * `reset` (project switch) drops counts first so a failing re-poll hides
     * the badge; the periodic poll omits it to avoid flicker.
     */
    async refreshBadges(reset = false) {
      if (reset) this.badgeCounts = {}
      const entries: MenuEntry[] = []
      for (const item of this.items) {
        if (item.type === 'entry') entries.push(item)
        else entries.push(...item.entries)
      }
      await Promise.all(
        entries
          .filter((e) => e.badgePath)
          .map(async (e) => {
            try {
              const res = await http.get<{ count: number }>(e.badgePath as string)
              this.badgeCounts[e.path] = res.data.count
            } catch {
              // keep the last known count
            }
          }),
      )
    },
    /** Keep the menu (and, piggybacked, the project list) in sync with
     *  extension installs/uninstalls and project create/remove. */
    startPolling() {
      if (this.pollTimer) return
      const project = useProjectStore()
      this.pollTimer = setInterval(() => {
        // Transient failures keep the last known menu / project list.
        this.refresh().catch(() => {})
        project.refreshProjects()
      }, POLL_INTERVAL_MS)
    },
  },
})
