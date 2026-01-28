<template>
    <div>
        <v-btn block depressed color="primary" class="blue darken-1" @click="dialog = true" title="Notifications">
            <v-icon>{{ notifications.length > 0 ? 'mdi-bell-ring' : 'mdi-bell-outline' }}</v-icon>
            <span class="ml-1">{{ total }}</span>
        </v-btn>

        <template>
            <v-dialog v-model="dialog" max-width="800">
                <v-card>
                    <v-card-title class="headline">
                        <v-icon>mdi-bell</v-icon>
                        <h3 class="ml-2">Notifications</h3>
                        <v-spacer />
                        <v-btn color="primary" @click="markAllAsRead">
                            <v-icon>mdi-check</v-icon>
                            Mark all as read
                        </v-btn>
                    </v-card-title>

                    <!-- only this wrapper scrolls -->
                    <v-card-text class="pa-0">
                        <div 
                            ref="scrollContainer" 
                            @scroll="onScroll" 
                            style="max-height: 1000px; overflow-y: auto;"
                            >
                            <v-expansion-panels multiple :value="defaultActivePanels">
                            <v-expansion-panel
                                v-for="(items, topic) in groupedNotifications"
                                :key="topic"
                            >
                                <v-expansion-panel-header>
                                <h3>{{ topic }}</h3>
                                </v-expansion-panel-header>

                                <v-expansion-panel-content>
                                <v-list two-line>
                                    <v-list-item
                                    v-for="notif in items"
                                    :key="notif.id"
                                    >
                                    <v-list-item-avatar>
                                        <v-icon>{{ notif.icon || 'mdi-information' }}</v-icon>
                                    </v-list-item-avatar>

                                    <v-list-item-content>
                                        <v-list-item-title>{{ notif.title }}</v-list-item-title>
                                        <v-list-item-subtitle>
                                        {{ new Date(notif.timestamp).toLocaleString() }}
                                        </v-list-item-subtitle>
                                        <div v-html="notif.description" class="mt-1"></div>
                                    </v-list-item-content>

                                    <v-list-item-action
                                        class="d-flex flex-row align-center"
                                        style="gap: 8px;"
                                    >
                                        <v-btn
                                        color="primary"
                                        icon
                                        small
                                        v-if="notif.link"
                                        :href="notif.link"
                                        target="_blank"
                                        >
                                        <v-icon>mdi-open-in-new</v-icon>
                                        </v-btn>

                                        <v-btn
                                        color="primary"
                                        text
                                        small
                                        @click="readNotification(notif.id)"
                                        >
                                        <v-icon>mdi-check-circle-outline</v-icon>
                                        </v-btn>
                                    </v-list-item-action>
                                    </v-list-item>
                                </v-list>


                                </v-expansion-panel-content>
                            </v-expansion-panel>
                            </v-expansion-panels>
                        </div>

                        <div v-if="notifications.length === 0" class="text-center grey--text pa-4">
                            No notifications
                        </div>
                    </v-card-text>

                    <v-card-actions>
                        <v-spacer />
                        <v-btn elevation="2" text @click="dialog = false">
                            Close
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>
        </template>


    </div>
</template>
<script lang="ts">
import Vue from 'vue'
import { NotificationWebsocket, fetch_notifications, read_notification, Notification, NotificationEvent } from "@/common/notification.service"

export default Vue.extend({
    name: "NotificationButton",
    data() {
        return {
            notificationws: null as NotificationWebsocket | null,
            notifications: [] as Notification[],
            dialog: false,
            
            // pagination state
            limit: 20,
            cursor: null as string | null,
            hasMore: true,
            total: 0 as number,
            loading: false,

            scrollThresholdPx: 150
        };
    },

  computed: {
    groupedNotifications(): Record<string, Notification[]> {
      return this.notifications.reduce((groups, notif) => {
        const key = notif.topic || 'Other'
        if (!groups[key]) groups[key] = []
        groups[key].push(notif)
        return groups
      }, {} as Record<string, Notification[]>)
    },

    defaultActivePanels(): number[] {
      return Object.keys(this.groupedNotifications).map((_, i) => i)
    }
  },

  methods: {
    /* -----------------------------
     * Pagination / fetching
     * ----------------------------- */

    async updateNotifications() {
      // reset and load newest
      this.notifications = []
      this.cursor = null
      this.hasMore = true

      await this.loadMoreNotifications()
    },

    async loadMoreNotifications() {
      if (this.loading || !this.hasMore) return

      this.loading = true
      try {
        const response = await fetch_notifications({
          limit: this.limit,
          cursor: this.cursor
        })

        if (!response) return
        const { data, meta } = response

        this.notifications.push(...data)
        this.cursor = meta.nextCursor
        this.hasMore = meta.hasMore
        this.total = meta.total
      } catch (err) {
        console.error("Failed to load notifications", err)
      } finally {
        this.loading = false
      }
    },

    onScroll() {
      const el = this.$refs.scrollContainer as HTMLElement
      if (!el) return

      const distanceFromBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight

      if (distanceFromBottom < this.scrollThresholdPx) {
        this.loadMoreNotifications()
      }
    },

    /* -----------------------------
     * Actions
     * ----------------------------- */

    readNotification(id: string) {
      read_notification(id).then(() => {
        this.notifications = this.notifications.filter(n => n.id !== id)
      })
    },

    markAllAsRead() {
      if (!this.notifications.length) return
      Promise.all(
        this.notifications.map(n => read_notification(n.id))
      ).then(() => this.updateNotifications())
    }
  },

  mounted() {
    this.notificationws = new NotificationWebsocket()
    this.notificationws.onMessage((data: NotificationEvent) => {
      // new notification → refresh from top
      this.updateNotifications()
    })

    this.updateNotifications()
  }
})
</script>