<script setup lang="ts">
import type { DataEntity } from '@/types/domain'

defineProps<{
  entity: DataEntity
  navigateToEntity: (id: string | null | undefined) => void
}>()
</script>

<template>
  <div class="hierarchy-tab">
    <div class="mb-4">
      <div class="text-caption text-medium-emphasis mb-2">Parent entity</div>
      <div v-if="entity.parent_id" class="mt-2">
        <v-btn
          size="small"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-arrow-up-bold"
          @click="navigateToEntity(entity.parent_id)"
        >
          {{ entity.parent_id }}
        </v-btn>
      </div>
      <v-alert v-else type="info" variant="tonal" density="comfortable">
        No Parent entity is linked.
      </v-alert>
    </div>
    <div>
      <div class="text-caption text-medium-emphasis mb-2">Child entities</div>
      <v-alert v-if="!entity.child_ids?.length" type="info" variant="tonal" density="comfortable">
        No child entities are linked.
      </v-alert>
      <v-list v-else density="compact">
        <v-list-item v-for="childId in entity.child_ids" :key="`hierarchy-${childId}`" :title="childId">
          <template #prepend>
            <v-icon color="primary" class="mr-2">mdi-subdirectory-arrow-right</v-icon>
          </template>
          <template #append>
            <v-btn icon variant="text" color="primary" @click="navigateToEntity(childId)">
              <v-icon>mdi-open-in-new</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </div>
  </div>
</template>
