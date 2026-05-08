<template>
  <v-row class="d-flex justify-center">
    <v-col cols="12">
      <v-alert :type="type" prominent>
        <slot>{{ message }}</slot>
      </v-alert>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  message?: string
  type?: 'info' | 'warning' | 'success' | 'error'
}>(), {
  type: 'info',
})
</script>
