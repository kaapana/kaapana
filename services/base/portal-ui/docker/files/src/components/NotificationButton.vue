<script setup lang="ts">
import { computed, ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { useNotificationsStore } from '@/stores/notifications'
import type { KaapanaNotification } from '@/api/notifications'

const notifications = useNotificationsStore()

const dialog = ref(false)
const confirmMarkAll = ref(false)
const scrollContainer = ref<HTMLElement | null>(null)
const scrollThresholdPx = 150

const groupedNotifications = computed<Record<string, KaapanaNotification[]>>(() =>
  notifications.notifications.reduce(
    (groups, notif) => {
      const key = notif.topic || 'Other'
      if (!groups[key]) groups[key] = []
      groups[key].push(notif)
      return groups
    },
    {} as Record<string, KaapanaNotification[]>,
  ),
)

const defaultActivePanels = computed(() =>
  Object.keys(groupedNotifications.value).map((_, i) => i),
)

function markRead(id: string) {
  notifications.read(id).catch((err) => {
    console.log(err)
    notify({
      type: 'error',
      title: 'Could not mark as read',
      text: 'The notification is still unread. Please try again.',
    })
  })
}

// Reads are irreversible and cover every unread notification, loaded or not.
const markAllText = computed(() => {
  const n = notifications.total
  return `${n} ${n === 1 ? 'notification' : 'notifications'} will be marked as read. This cannot be undone.`
})

function markAllAsRead() {
  confirmMarkAll.value = false
  notifications.markAllAsRead().catch((err) => {
    console.log(err)
    notify({
      type: 'error',
      title: 'Could not mark all as read',
      text: 'The notifications are still unread. Please try again.',
    })
  })
}

function onScroll() {
  const el = scrollContainer.value
  if (!el) return
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  if (distanceFromBottom < scrollThresholdPx) {
    notifications.loadMore()
  }
}
</script>

<template>
  <div>
    <v-btn icon variant="text" title="Notifications" @click="dialog = true">
      <v-badge :content="notifications.total" :model-value="notifications.total > 0" color="grey-darken-2">
        <v-icon>
          {{ notifications.notifications.length > 0 ? 'mdi-bell-ring' : 'mdi-bell-outline' }}
        </v-icon>
      </v-badge>
    </v-btn>

    <v-dialog v-model="dialog" max-width="800">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon>mdi-bell</v-icon>
          <h3 class="ml-2">Notifications</h3>
          <v-spacer />
          <v-btn color="primary" :disabled="notifications.total === 0" @click="confirmMarkAll = true">
            <v-icon>mdi-check</v-icon>
            Mark all as read
          </v-btn>
        </v-card-title>

        <!-- only this wrapper scrolls -->
        <v-card-text class="pa-0">
          <div ref="scrollContainer" class="notification-scroll" @scroll="onScroll">
            <v-expansion-panels multiple :model-value="defaultActivePanels">
              <v-expansion-panel v-for="(items, topic) in groupedNotifications" :key="topic">
                <v-expansion-panel-title>
                  <h3>{{ topic }}</h3>
                </v-expansion-panel-title>

                <v-expansion-panel-text>
                  <v-list lines="two">
                    <v-list-item v-for="notif in items" :key="notif.id">
                      <template #prepend>
                        <v-icon>{{ notif.icon || 'mdi-information' }}</v-icon>
                      </template>

                      <v-list-item-title>{{ notif.title }}</v-list-item-title>
                      <v-list-item-subtitle>
                        {{ new Date(notif.timestamp).toLocaleString() }}
                      </v-list-item-subtitle>
                      <!-- eslint-disable-next-line vue/no-v-html -->
                      <div class="mt-1" v-html="notif.description"></div>

                      <template #append>
                        <v-btn
                          v-if="notif.link"
                          color="primary"
                          icon
                          size="small"
                          variant="text"
                          :href="notif.link"
                          target="_blank"
                        >
                          <v-icon>mdi-open-in-new</v-icon>
                        </v-btn>
                        <v-btn
                          color="primary"
                          variant="text"
                          size="small"
                          @click="markRead(notif.id)"
                        >
                          <v-icon>mdi-check-circle-outline</v-icon>
                        </v-btn>
                      </template>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <div
            v-if="notifications.notifications.length === 0"
            class="text-center text-grey pa-4"
          >
            No notifications
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn elevation="2" variant="text" @click="dialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="confirmMarkAll" width="440">
      <v-card>
        <v-card-title>Mark all as read?</v-card-title>
        <v-card-text>{{ markAllText }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="confirmMarkAll = false">Cancel</v-btn>
          <v-btn color="primary" @click="markAllAsRead()">Mark all as read</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.notification-scroll {
  max-height: 1000px;
  overflow-y: auto;
}
</style>
