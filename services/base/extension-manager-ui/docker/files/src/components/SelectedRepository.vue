<script setup lang="ts">
import RepositoryForm from '@/components/RepositoryForm.vue'
import type { Repository, RepositoryFormState } from '@/types/schemas'

const props = defineProps<{
  selectedRepository?: Repository | null
  selectedRepositoryForm: RepositoryFormState
  editingSelectedRepository: boolean
  updatingSelectedRepository: boolean
  deletingSelectedRepository: boolean
  repositoryActionError?: string | null
}>()

const emit = defineEmits<{
  (event: 'clearSelectedRepository'): void
  (event: 'enableEditSelectedRepository'): void
  (event: 'cancelEditSelectedRepository'): void
  (event: 'update:selectedRepositoryForm', repositoryForm: RepositoryFormState): void
  (event: 'updateSelectedRepository'): void
  (event: 'deleteSelectedRepository'): void
}>()

function emitClearSelectedRepository() {
  emit('clearSelectedRepository')
}

function emitEnableEditSelectedRepository() {
  emit('enableEditSelectedRepository')
}

function emitCancelEditSelectedRepository() {
  emit('cancelEditSelectedRepository')
}

function emitSelectedRepositoryFormUpdate(repositoryForm: RepositoryFormState) {
  emit('update:selectedRepositoryForm', repositoryForm)
}

function emitUpdateSelectedRepository() {
  emit('updateSelectedRepository')
}

function emitDeleteSelectedRepository() {
  emit('deleteSelectedRepository')
}

function deleteSelectedRepositoryIfConfirmed() {
  if (!props.selectedRepository) return

  const confirmed = window.confirm(
    `Remove repository "${props.selectedRepository.name}"?`,
  )

  if (!confirmed) return

  emitDeleteSelectedRepository()
}
</script>

<template>
  <v-dialog :model-value="Boolean(props.selectedRepository)" max-width="720"
    @update:model-value="emitClearSelectedRepository">
    <v-card v-if="props.selectedRepository">
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <div class="text-h6">{{ props.selectedRepository.name }}</div>
          <div class="text-body-2 text-medium-emphasis">
            {{ props.selectedRepository.repository_url }}
          </div>
        </div>

        <v-btn icon="mdi-close" variant="text" size="small" title="Close" @click="emitClearSelectedRepository" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert v-if="props.repositoryActionError" type="error" density="compact" class="mb-4">
          {{ props.repositoryActionError }}
        </v-alert>

        <RepositoryForm v-if="props.editingSelectedRepository" :repository-form="props.selectedRepositoryForm"
          :submitting-repository-form="props.updatingSelectedRepository" submit-label="Save changes"
          :require-authentication="false" show-cancel-button @update:repository-form="emitSelectedRepositoryFormUpdate"
          @submit-repository-form="emitUpdateSelectedRepository"
          @cancel-repository-form="emitCancelEditSelectedRepository" />

        <div v-else class="d-flex flex-column ga-3">
          <div>
            <div class="text-caption text-medium-emphasis">Repository ID</div>
            <div class="text-body-2">{{ props.selectedRepository.id }}</div>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis">Name</div>
            <div class="text-body-2">{{ props.selectedRepository.name }}</div>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis">Repository URL</div>
            <div class="text-body-2">{{ props.selectedRepository.repository_url }}</div>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis">Description</div>
            <div class="text-body-2">
              {{ props.selectedRepository.description || 'No description provided.' }}
            </div>
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions v-if="!props.editingSelectedRepository">
        <v-spacer />

        <v-btn color="error" variant="text" :loading="props.deletingSelectedRepository"
          :disabled="props.updatingSelectedRepository" @click="deleteSelectedRepositoryIfConfirmed">
          Remove
        </v-btn>

        <v-btn color="primary" variant="tonal" :disabled="props.deletingSelectedRepository"
          @click="emitEnableEditSelectedRepository">
          Modify
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
