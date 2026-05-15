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
      <v-card-title>{{ slotProps.item.name }}</v-card-title>
      <v-card-subtitle>{{ slotProps.item.repository_url }}</v-card-subtitle>
      <v-card-text v-if="slotProps.item.description">
        {{ slotProps.item.description }}
      </v-card-text>
    </template>
  </BaseCardIterator>
</template>
