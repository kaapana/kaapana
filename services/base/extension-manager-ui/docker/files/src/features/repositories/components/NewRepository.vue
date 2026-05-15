<script setup lang="ts">
import RepositoryForm from '@/features/repositories/components/RepositoryForm.vue'
import type { RepositoryFormState } from '@/features/repositories/types'

const props = defineProps<{
  showingNewRepositoryDialog: boolean
  createRepositoryForm: RepositoryFormState
  creatingRepository: boolean
  createRepositoryError?: string | null
}>()

const emit = defineEmits<{
  (event: 'clearNewRepositoryDialog'): void
  (event: 'update:createRepositoryForm', repositoryForm: RepositoryFormState): void
  (event: 'createNewRepository'): void
}>()

function emitClearNewRepositoryDialog() {
  emit('clearNewRepositoryDialog')
}

function emitCreateRepositoryFormUpdate(repositoryForm: RepositoryFormState) {
  emit('update:createRepositoryForm', repositoryForm)
}

function emitCreateNewRepository() {
  emit('createNewRepository')
}
</script>

<template>
  <v-dialog
    :model-value="props.showingNewRepositoryDialog"
    max-width="720"
    @update:model-value="emitClearNewRepositoryDialog"
  >
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <div class="text-h6">New repository</div>
          <div class="text-body-2 text-medium-emphasis">Add an OCI registry repository.</div>
        </div>

        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          title="Close"
          @click="emitClearNewRepositoryDialog"
        />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert v-if="props.createRepositoryError" type="error" density="compact" class="mb-4">
          {{ props.createRepositoryError }}
        </v-alert>

        <RepositoryForm
          :repository-form="props.createRepositoryForm"
          :submitting-repository-form="props.creatingRepository"
          submit-label="Add repository"
          require-authentication
          show-cancel-button
          @update:repository-form="emitCreateRepositoryFormUpdate"
          @submit-repository-form="emitCreateNewRepository"
          @cancel-repository-form="emitClearNewRepositoryDialog"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
