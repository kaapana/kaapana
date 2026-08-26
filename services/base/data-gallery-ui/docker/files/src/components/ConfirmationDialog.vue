<template>
  <v-dialog :model-value="show" @update:model-value="emit('update:show', $event)" max-width="500">
    <v-card>
      <v-card-title class="text-h5">{{ title }}</v-card-title>
      <v-card-text>
        <slot></slot>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="emit('confirm')">{{ confirmText }}</v-btn>
        <v-btn @click="emit('cancel')">{{ cancelText }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    show: boolean
    title?: string
    cancelText?: string
    confirmText?: string
  }>(),
  {
    title: 'Confirm',
    cancelText: 'Cancel',
    confirmText: 'Confirm',
  },
)

const emit = defineEmits<{ cancel: []; confirm: []; 'update:show': [value: boolean] }>()
</script>
