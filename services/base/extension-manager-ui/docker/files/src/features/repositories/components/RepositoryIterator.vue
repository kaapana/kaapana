<script setup lang="ts">
import type { Repository } from '@/shared/types/apiSchemas'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'

defineProps<{
  repositories: Repository[]
  loadingRepositories: boolean
  repositoryError?: string | null
}>()

defineEmits<{
  (event: 'selectRepository', repository: Repository): void
}>()
</script>

<template>
  <BaseCardIterator
    :items="repositories"
    :loading="loadingRepositories"
    :error="repositoryError"
    empty-message="No repositories registered."
    :item-key="(repository) => repository.id"
    @select="$emit('selectRepository', $event)"
  >
    <template v-slot:cardBody="slotProps">
      <div class="repository-card">
        <v-card-title>{{ slotProps.item.name }}</v-card-title>
        <v-divider />
        <v-card-text class="repository-card-meta">
          <div class="text-medium-emphasis">{{ slotProps.item.repository_url }}</div>
          <div v-if="slotProps.item.description">{{ slotProps.item.description }}</div>
        </v-card-text>
      </div>
    </template>
  </BaseCardIterator>
</template>

<style scoped>
.repository-card {
  text-align: left;
}

.repository-card-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
