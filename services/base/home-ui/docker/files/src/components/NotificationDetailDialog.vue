<template>
  <v-dialog :model-value="modelValue" max-width="600" @update:model-value="emit('update:modelValue', $event)">
    <v-card v-if="notification">
      <v-card-title class="d-flex align-start">
        <v-icon class="mr-2">{{ notification.icon || 'mdi-information' }}</v-icon>
        <span class="detail-title">{{ notification.title }}</span>
        <v-spacer />
        <v-btn icon variant="text" aria-label="Close" @click="emit('update:modelValue', false)">
          <v-icon>{{ kaapanaIcons.close }}</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-subtitle>{{ new Date(notification.timestamp).toLocaleString() }}</v-card-subtitle>
      <v-card-text>
        <!-- The description is server-authored HTML. -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="text-body-2" v-html="notification.description"></div>
      </v-card-text>
      <v-card-actions>
        <v-btn
          v-if="notification.link"
          color="primary"
          variant="text"
          prepend-icon="mdi-open-in-new"
          :href="notification.link"
          target="_top"
        >
          Open
        </v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          variant="text"
          prepend-icon="mdi-check-circle-outline"
          :loading="submitting"
          :disabled="submitting"
          @click="markRead"
        >
          Mark as read
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaIcons } from '@kaapana/base-ui'
import { useNotificationsStore } from '@/stores/notifications'
import type { KaapanaNotification } from '@/api/notifications'

const props = defineProps<{ modelValue: boolean; notification: KaapanaNotification | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const notifications = useNotificationsStore()

// Marks the button busy, which also keeps a second click from sending the
// request again while the first one is still running.
const submitting = ref(false)

// read() drops the notification from the store, so the dialog would be left
// showing an entry that no longer exists anywhere else.
async function markRead() {
  submitting.value = true
  try {
    await notifications.read(props.notification!.id)
  } catch (err: any) {
    // A failed PUT (deleted notification, network loss) must still dismiss the
    // dialog — leaving it open strands the user on the action they just clicked.
    notify({
      type: 'error',
      title: 'Failed to mark as read',
      text: err?.response?.data?.detail ?? err?.message,
    })
  } finally {
    // The dialog is reused for the next notification, so the flag must not
    // stay set once this request is done.
    submitting.value = false
  }
  emit('update:modelValue', false)
}
</script>

<style scoped>
/* The dialog is the full view of a notification: let a long title wrap rather
   than inherit the card title's single-line clipping. */
.detail-title {
  white-space: normal;
  word-break: break-word;
}
</style>
