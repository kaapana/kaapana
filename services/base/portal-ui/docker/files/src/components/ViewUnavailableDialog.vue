<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { VBtn } from 'vuetify/components'

// Shown when an embedded view asks for a route the menu cannot offer (see the
// kaapana:navigate handler in App.vue).
const props = defineProps<{ target: string | null }>()
defineEmits<{ close: [] }>()

const closeButton = ref<InstanceType<typeof VBtn> | null>(null)

// The only action takes the initial focus, so Enter dismisses the dialog.
watch(
  () => props.target,
  async (target) => {
    if (target === null) return
    await nextTick()
    closeButton.value?.$el?.focus()
  },
)
</script>

<template>
  <v-dialog :model-value="target !== null" max-width="400" @update:model-value="$emit('close')">
    <v-card>
      <v-card-title>View unavailable</v-card-title>
      <v-card-text>
        This platform has no view at <code>{{ target }}</code
        >, or your role may not open it. If it belongs to an extension, check that the extension is
        installed.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn ref="closeButton" color="primary" @click="$emit('close')">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
