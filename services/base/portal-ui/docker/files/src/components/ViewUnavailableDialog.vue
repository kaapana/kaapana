<script setup lang="ts">
// Shown when an embedded view asks for a route the menu cannot offer (see the
// kaapana:navigate handler in App.vue).
defineProps<{ target: string | null }>()
defineEmits<{ close: [] }>()
</script>

<template>
  <v-dialog :model-value="target !== null" width="440" @update:model-value="$emit('close')">
    <v-card>
      <v-card-title>View unavailable</v-card-title>
      <v-card-text>
        This platform has no view at <code>{{ target }}</code
        >, or your role may not open it. If it belongs to an extension, check
        that the extension is installed.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" @click="$emit('close')">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
