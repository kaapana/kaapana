<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-badge :content="notifications.total" :model-value="notifications.total > 0" color="primary">
        <v-icon>{{ notifications.total > 0 ? 'mdi-bell-ring' : 'mdi-bell-outline' }}</v-icon>
      </v-badge>
      <span class="ml-3">Notifications</span>
    </v-card-title>
    <v-card-text class="pa-0">
      <div
        v-if="notifications.notifications.length === 0"
        class="text-center text-medium-emphasis pa-4"
      >
        No notifications — you're all caught up
      </div>
      <div v-else ref="scrollContainer" class="notification-scroll" @scroll="onScroll">
        <v-list lines="two" density="compact">
        <v-list-item
          v-for="notif in notifications.notifications"
          :key="notif.id"
          @click="openDetail(notif)"
        >
          <template #prepend>
            <v-icon>{{ notif.icon || 'mdi-information' }}</v-icon>
          </template>
          <v-list-item-title>{{ notif.title }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ new Date(notif.timestamp).toLocaleString() }}
          </v-list-item-subtitle>
        </v-list-item>
        </v-list>
        <v-progress-linear v-if="notifications.loading" indeterminate />
      </div>
    </v-card-text>

    <NotificationDetailDialog v-model="detailOpen" :notification="selected" />
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NotificationDetailDialog from '@/components/NotificationDetailDialog.vue'
import { useNotificationsStore } from '@/stores/notifications'
import type { KaapanaNotification } from '@/api/notifications'

const notifications = useNotificationsStore()

// Hold the notification itself rather than its id: read() drops the entry from
// the store, and the dialog still has to render it while it closes.
const selected = ref<KaapanaNotification | null>(null)
const detailOpen = ref(false)

function openDetail(notif: KaapanaNotification) {
  selected.value = notif
  detailOpen.value = true
}

const scrollContainer = ref<HTMLElement | null>(null)
const scrollThresholdPx = 150

function onScroll() {
  const el = scrollContainer.value
  if (!el) return
  if (el.scrollHeight - el.scrollTop - el.clientHeight < scrollThresholdPx) {
    notifications.loadMore()
  }
}

// connect() opens the websocket and triggers the initial fetch.
onMounted(() => notifications.connect())
</script>

<style scoped>
.notification-scroll {
  max-height: 420px;
  overflow-y: auto;
}
</style>
