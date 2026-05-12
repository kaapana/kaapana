<script setup lang="ts">
import ToggleDarkMode from '@/components/toggleDarkMode.vue'

defineProps<{
  loading: boolean
  repositoryCount: number
  catalogEntryCount: number
}>()

const emit = defineEmits<{
  (event: 'fetch'): void
}>()
</script>

<template>
  <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
    <div>
      <h1 class="text-h5 mb-1">Extension Catalog</h1>
      <div class="text-body-2 text-medium-emphasis">
        {{ repositoryCount }} repositories · {{ catalogEntryCount }} catalog entries
      </div>
    </div>

    <div class="d-flex align-center ga-2">
      <ToggleDarkMode />
      <v-btn variant="outlined" color="primary" to="/extensions">
        <v-icon start>mdi-database-cog</v-icon>
        Manage extensions
      </v-btn>
      <v-btn variant="outlined" color="primary" to="/repositories">
        <v-icon start>mdi-database-cog</v-icon>
        Manage repositories
      </v-btn>
      <v-btn color="primary" :loading="loading" @click="emit('fetch')">
        <v-icon start>mdi-cloud-sync</v-icon>
        Fetch from OCI repositories
      </v-btn>
    </div>
  </div>
</template>
