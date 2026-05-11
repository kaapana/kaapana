<script setup lang="ts">
import ToggleDarkMode from '@/components/toggleDarkMode.vue'

defineProps<{
  loading: boolean
  repositoryCount: number
  extensionCount: number
}>()

const emit = defineEmits<{
  (event: 'fetch'): void
}>()
</script>

<template>
  <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
    <div>
      <h1 class="text-h5 mb-1">Extension Manager</h1>
      <div class="text-body-2 text-medium-emphasis">
        {{ repositoryCount }} repositories · {{ extensionCount }} extensions
      </div>
    </div>

    <div class="d-flex align-center ga-2">
      <ToggleDarkMode />

      <v-btn
        color="primary"
        :loading="loading"
        @click="emit('fetch')"
      >
        <v-icon start>mdi-cloud-sync</v-icon>
        Fetch from OCI repositories
      </v-btn>
    </div>
  </div>
</template>
