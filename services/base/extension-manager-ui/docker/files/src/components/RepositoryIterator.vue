<script setup lang="ts">
import type { Repository } from '@/types/schemas'

const props = defineProps<{
  repositories: Repository[]
  loadingRepositories: boolean
  repositoryError?: string | null
}>()

const emit = defineEmits<{
  (event: 'selectRepository', repository: Repository): void
}>()

function emitSelectRepository(repository: Repository) {
  emit('selectRepository', repository)
}
</script>

<template>
  <v-alert v-if="props.repositoryError" type="error" class="mb-4">
    {{ props.repositoryError }}
  </v-alert>

  <v-row v-else-if="props.loadingRepositories" class="d-flex justify-center align-center" style="min-height: 240px;">
    <v-progress-circular indeterminate color="primary" size="64" />
  </v-row>

  <v-alert v-else-if="props.repositories.length === 0" type="info" class="mb-4">
    No repositories registered.
  </v-alert>

  <v-row v-else>
    <v-col
      v-for="repository in props.repositories"
      :key="repository.id"
      cols="12"
      md="6"
      lg="4"
    >
      <v-card
        class="h-100"
        role="button"
        tabindex="0"
        @click="emitSelectRepository(repository)"
      >
        <v-card-title>
          {{ repository.name }}
        </v-card-title>

        <v-card-subtitle>
          {{ repository.repository_url }}
        </v-card-subtitle>

        <v-card-text v-if="repository.description">
          {{ repository.description }}
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
