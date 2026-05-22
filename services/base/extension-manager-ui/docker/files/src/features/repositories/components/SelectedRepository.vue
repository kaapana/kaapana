<script setup lang="ts">
import { ref } from 'vue'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import RepositoryForm from '@/features/repositories/components/RepositoryForm.vue'
import type { Repository } from '@/shared/types/apiSchemas'
import type { RepositoryFormState } from '@/features/repositories/types'

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

const showDeleteConfirm = ref(false)

function requestDelete() {
  if (!props.selectedRepository) return
  showDeleteConfirm.value = true
}

function onDeleteConfirmed() {
  emit('deleteSelectedRepository')
}
</script>

<template>
  <BaseDetailDialog
    :open="Boolean(props.selectedRepository)"
    :title="props.selectedRepository?.name"
    :subtitle="props.selectedRepository?.repository_url"
    :error="props.repositoryActionError"
    @close="$emit('clearSelectedRepository')"
  >
    <template v-if="props.selectedRepository" v-slot:body>
      <RepositoryForm
        v-if="props.editingSelectedRepository"
        :repository-form="props.selectedRepositoryForm"
        :submitting-repository-form="props.updatingSelectedRepository"
        submit-label="Save changes"
        show-cancel-button
        @update:repository-form="$emit('update:selectedRepositoryForm', $event)"
        @submit-repository-form="$emit('updateSelectedRepository')"
        @cancel-repository-form="$emit('cancelEditSelectedRepository')"
      />

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
    </template>

    <template v-if="!props.editingSelectedRepository" v-slot:actions>
      <v-btn
        color="error"
        variant="text"
        :loading="props.deletingSelectedRepository"
        :disabled="props.updatingSelectedRepository"
        @click="requestDelete"
      >
        Remove
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        :disabled="props.deletingSelectedRepository"
        @click="$emit('enableEditSelectedRepository')"
      >
        Modify
      </v-btn>
    </template>
  </BaseDetailDialog>

  <ConfirmDialog
    v-model="showDeleteConfirm"
    title="Remove repository"
    :message="`Remove repository &quot;${props.selectedRepository?.name ?? ''}&quot;?`"
    confirm-label="Remove"
    @confirm="onDeleteConfirmed"
  />
</template>
