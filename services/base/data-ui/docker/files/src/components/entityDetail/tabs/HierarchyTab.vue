<script setup lang="ts">
import type { DataEntity } from '@/types/domain'
import { icons } from '@/utils/icons'

defineProps<{ entity: DataEntity }>()
const emit = defineEmits<{ (e: 'navigate', id: string): void }>()
</script>

<template>
  <div>
    <h3 class="text-subtitle-1 mb-1">Parent</h3>
    <v-btn
      v-if="entity.parent_id"
      variant="text"
      :prepend-icon="icons.parent"
      class="mb-4"
      @click="emit('navigate', entity.parent_id)"
    >
      {{ entity.parent_id }}
    </v-btn>
    <p v-else class="text-body-2 text-medium-emphasis mb-4">The entity has no parent.</p>

    <h3 class="text-subtitle-1 mb-1">Children</h3>
    <v-list v-if="entity.child_ids?.length" density="compact">
      <v-list-item
        v-for="childId in entity.child_ids"
        :key="childId"
        :title="childId"
        :prepend-icon="icons.child"
        :aria-label="`Show child entity ${childId}`"
        @click="emit('navigate', childId)"
      />
    </v-list>
    <p v-else class="text-body-2 text-medium-emphasis">The entity has no children.</p>
  </div>
</template>
