import { defineStore } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import {
  fetchNotifications,
  readNotification,
  NotificationWebsocket,
  NotificationEventType,
  type KaapanaNotification,
} from '@/api/notifications'

const PAGE_LIMIT = 20

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    notifications: [] as KaapanaNotification[],
    cursor: null as string | null,
    hasMore: true,
    total: 0,
    loading: false,
    refreshId: 0,
    ws: null as NotificationWebsocket | null,
  }),
  actions: {
    connect() {
      if (this.ws) return
      this.ws = new NotificationWebsocket()
      this.ws.onMessage(async (event) => {
        await this.refresh()
        if (event.type === NotificationEventType.NEW) {
          const newest = this.notifications.find((n) => n.id === event.id)
          if (newest) {
            notify({ title: newest.title, text: newest.description, type: 'info' })
          }
        }
      })
      this.refresh()
    },
    async refresh() {
      // Invalidate any in-flight loadMore so its (now stale) page cannot commit
      // into the cleared list, and drop the loading guard so this refresh's own
      // load runs instead of being swallowed by that pending fetch.
      this.refreshId += 1
      this.notifications = []
      this.cursor = null
      this.hasMore = true
      this.loading = false
      await this.loadMore()
    },
    async loadMore() {
      if (this.loading || !this.hasMore) return
      const refreshId = this.refreshId
      this.loading = true
      try {
        const { data, meta } = await fetchNotifications({
          limit: PAGE_LIMIT,
          cursor: this.cursor,
        })
        // A refresh happened while this fetch was in flight: its page belongs to
        // the old cursor, so discard it rather than pushing stale items.
        if (refreshId !== this.refreshId) return
        this.notifications.push(...data)
        this.cursor = meta.nextCursor
        this.hasMore = meta.hasMore
        this.total = meta.total
      } catch (err) {
        console.error('Failed to load notifications', err)
        notify({
          type: 'error',
          title: 'Could not load notifications',
          text: 'The notification list could not be loaded. Please try again later.',
        })
      } finally {
        // Only release the guard if we still own it; a superseding refresh's
        // load owns it now and must stay protected from concurrent scrolls.
        if (refreshId === this.refreshId) this.loading = false
      }
    },
    async read(id: string) {
      await readNotification(id)
      this.notifications = this.notifications.filter((n) => n.id !== id)
    },
    async markAllAsRead() {
      if (!this.notifications.length) return
      await Promise.all(this.notifications.map((n) => readNotification(n.id)))
      await this.refresh()
    },
  },
})
