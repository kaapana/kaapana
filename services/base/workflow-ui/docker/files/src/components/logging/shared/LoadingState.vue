<template>
  <v-row class="d-flex justify-center align-center" :style="{ minHeight }">
    <v-progress-circular indeterminate color="primary" :size="size" />
  </v-row>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  size?: number
  minHeight?: string
}>(), {
  size: 64,
  minHeight: '300px',
})
</script>
