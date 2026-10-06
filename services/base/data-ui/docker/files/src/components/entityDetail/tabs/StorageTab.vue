<script setup lang="ts">
import type { DataEntity } from '@/types/domain'
import { formatStorage } from '@/utils/format'

defineProps<{ entity: DataEntity }>()
</script>

<template>
  <v-list v-if="entity.storage_coordinates.length" density="comfortable" lines="two">
    <v-list-item
      v-for="(coord, index) in entity.storage_coordinates"
      :key="`${entity.id}-${index}`"
      :title="coord.type"
      :subtitle="formatStorage(coord)"
    />
  </v-list>
  <p v-else class="text-body-2 text-medium-emphasis">
    No storage location is registered for this entity.
  </p>
</template>
