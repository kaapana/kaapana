<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { VCardText } from 'vuetify/components'
import { ConfirmDialog, kaapanaIcons } from '@kaapana/base-ui'
import { notifyFailure } from '@/utils/notifyFailure'
import { useNotificationsStore } from '@/stores/notifications'
import type { KaapanaNotification } from '@/api/notifications'

const notifications = useNotificationsStore()

const dialog = ref(false)
const confirmMarkAll = ref(false)
// The scrolling card text of the `scrollable` dialog.
const scrollContainer = ref<InstanceType<typeof VCardText> | null>(null)
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

const defaultActivePanels = computed(() => Object.keys(groupedNotifications.value).map((_, i) => i))

// Ids with a mark-read request in progress. Their buttons show a spinner and
// ignore further clicks until the request is done.
const pendingReads = reactive(new Set<string>())
const markingAll = ref(false)

async function markRead(id: string) {
  if (pendingReads.has(id)) return
  pendingReads.add(id)
  try {
    await notifications.read(id)
  } catch (err) {
    console.error(err)
    notifyFailure(
      'Could not mark as read',
      'The notification is still unread. Please try again.',
      err,
    )
  } finally {
    pendingReads.delete(id)
  }
}

// Reads are irreversible and cover every unread notification, loaded or not.
const markAllText = computed(() => {
  const n = notifications.total
  return `${n} ${n === 1 ? 'notification' : 'notifications'} will be marked as read. This cannot be undone.`
})

async function markAllAsRead() {
  markingAll.value = true
  try {
    await notifications.markAllAsRead()
  } catch (err) {
    console.error(err)
    notifyFailure(
      'Could not mark all as read',
      'The notifications are still unread. Please try again.',
      err,
    )
  } finally {
    markingAll.value = false
  }
}

function onScroll() {
  const el = scrollContainer.value?.$el as HTMLElement | undefined
  if (!el) return
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  if (distanceFromBottom < scrollThresholdPx) {
    notifications.loadMore()
  }
}
</script>

<template>
  <div>
    <!-- Without an explicit name, the button would take the badge's label as
         its name. -->
    <v-btn
      icon
      variant="text"
      title="Notifications"
      :aria-label="
        notifications.total > 0 ? `Notifications, ${notifications.total} unread` : 'Notifications'
      "
      @click="dialog = true"
    >
      <v-badge
        :content="notifications.total"
        :model-value="notifications.total > 0"
        label="unread notifications"
        color="grey-darken-2"
      >
        <v-icon
          :icon="
            notifications.notifications.length > 0
              ? kaapanaIcons.notificationsUnread
              : kaapanaIcons.notifications
          "
        ></v-icon>
      </v-badge>
    </v-btn>

    <v-dialog v-model="dialog" max-width="900" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon :icon="kaapanaIcons.notifications"></v-icon>
          <span class="ml-2">Notifications</span>
        </v-card-title>
        <!-- Shown while the first page or a further page loads. -->
        <v-progress-linear
          :active="notifications.loading"
          indeterminate
          color="primary"
          aria-label="Loading notifications"
        ></v-progress-linear>

        <!-- With `scrollable`, this element scrolls. Scrolling near the end loads
             the next page. -->
        <v-card-text ref="scrollContainer" class="pa-0" @scroll.passive="onScroll">
          <v-expansion-panels multiple :model-value="defaultActivePanels">
            <v-expansion-panel v-for="(items, topic) in groupedNotifications" :key="topic">
              <v-expansion-panel-title>
                <span class="text-subtitle-1 font-weight-medium">{{ topic }}</span>
              </v-expansion-panel-title>

              <v-expansion-panel-text>
                <v-list lines="three">
                  <v-list-item v-for="notif in items" :key="notif.id">
                    <template #prepend>
                      <v-icon :icon="notif.icon || kaapanaIcons.info"></v-icon>
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
                        :icon="kaapanaIcons.externalLink"
                        color="primary"
                        size="small"
                        variant="text"
                        title="Open link"
                        :href="notif.link"
                        target="_blank"
                      ></v-btn>
                      <v-btn
                        :icon="kaapanaIcons.success"
                        color="primary"
                        variant="text"
                        size="small"
                        title="Mark as read"
                        :loading="pendingReads.has(notif.id)"
                        :disabled="pendingReads.has(notif.id)"
                        @click="markRead(notif.id)"
                      ></v-btn>
                    </template>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- An empty list means the load failed, is still running, or found
               nothing. Each case gets its own state. -->
          <template v-if="notifications.notifications.length === 0">
            <v-empty-state
              v-if="notifications.error"
              :icon="kaapanaIcons.error"
              title="Could not load notifications"
              text="Try again, or contact your administrator if it persists."
              size="56"
            >
              <template #actions>
                <v-btn
                  color="primary"
                  variant="text"
                  :loading="notifications.loading"
                  @click="notifications.refresh()"
                >
                  Try again
                </v-btn>
              </template>
            </v-empty-state>
            <v-empty-state
              v-else-if="!notifications.loading"
              title="No notifications"
              text="New notifications appear here as they arrive."
              size="56"
            ></v-empty-state>
          </template>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Close</v-btn>
          <!-- The dialog's only primary action. -->
          <v-btn
            color="primary"
            variant="flat"
            :loading="markingAll"
            :disabled="notifications.total === 0 || markingAll"
            @click="confirmMarkAll = true"
          >
            Mark all as read
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Marking as read cannot be undone, so it is confirmed as destructive. -->
    <ConfirmDialog
      v-model="confirmMarkAll"
      color="error"
      title="Mark all as read?"
      :text="markAllText"
      confirm-text="Mark all as read"
      @confirm="markAllAsRead"
    />
  </div>
</template>
