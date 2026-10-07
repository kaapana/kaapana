<script setup lang="ts">
import type { DataEntity } from '@/types/domain'

defineProps<{
  entity: DataEntity
  formatStorage: (storage: DataEntity['storage_coordinates'][number]) => string
}>()
</script>

<template>
  <v-list density="comfortable" lines="two">
    <v-list-item
      v-for="(coord, index) in entity.storage_coordinates"
      :key="`${entity.id}-${index}`"
      :title="coord.type"
      :subtitle="formatStorage(coord)"
    >
      <template #prepend>
        <v-avatar size="28" color="primary" variant="tonal">{{ index + 1 }}</v-avatar>
      </template>
    </v-list-item>
    <v-list-item v-if="!entity.storage_coordinates.length" title="No coordinates registered" />
  </v-list>
</template>
