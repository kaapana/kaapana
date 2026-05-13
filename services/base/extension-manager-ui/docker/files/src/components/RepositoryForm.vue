<script setup lang="ts">
import { computed } from 'vue'
import type { RepositoryFormState } from '@/types/schemas'

const props = defineProps<{
  repositoryForm: RepositoryFormState
  submittingRepositoryForm: boolean
  submitLabel: string
  requireAuthentication: boolean
  showCancelButton?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:repositoryForm', repositoryForm: RepositoryFormState): void
  (event: 'submitRepositoryForm'): void
  (event: 'cancelRepositoryForm'): void
}>()

const repositoryFormIsValid = computed(() =>
  Boolean(
    props.repositoryForm.name.trim()
    && props.repositoryForm.repository_url.trim()
    && (!props.requireAuthentication || props.repositoryForm.authentication.trim()),
  ),
)

function emitRepositoryFormUpdate(repositoryForm: RepositoryFormState) {
  emit('update:repositoryForm', repositoryForm)
}

function emitSubmitRepositoryForm() {
  emit('submitRepositoryForm')
}

function emitCancelRepositoryForm() {
  emit('cancelRepositoryForm')
}

function getUpdatedRepositoryForm(
  repositoryFormUpdate: Partial<RepositoryFormState>,
): RepositoryFormState {
  return {
    ...props.repositoryForm,
    ...repositoryFormUpdate,
  }
}

function updateRepositoryFormName(value: unknown) {
  emitRepositoryFormUpdate(getUpdatedRepositoryForm({ name: String(value ?? '') }))
}

function updateRepositoryFormDescription(value: unknown) {
  emitRepositoryFormUpdate(getUpdatedRepositoryForm({ description: String(value ?? '') }))
}

function updateRepositoryFormUrl(value: unknown) {
  emitRepositoryFormUpdate(getUpdatedRepositoryForm({ repository_url: String(value ?? '') }))
}

function updateRepositoryFormAuthentication(value: unknown) {
  emitRepositoryFormUpdate(getUpdatedRepositoryForm({ authentication: String(value ?? '') }))
}

function submitRepositoryForm() {
  if (!repositoryFormIsValid.value) return

  emitSubmitRepositoryForm()
}
</script>

<template>
  <v-form @submit.prevent="submitRepositoryForm">
    <v-row dense>
      <v-col cols="12" md="6">
        <v-text-field :model-value="props.repositoryForm.name" label="Name" density="compact" variant="outlined"
          required @update:model-value="updateRepositoryFormName" />
      </v-col>

      <v-col cols="12" md="6">
        <v-text-field :model-value="props.repositoryForm.repository_url" label="Repository URL" density="compact"
          variant="outlined" required @update:model-value="updateRepositoryFormUrl" />
      </v-col>

      <v-col cols="12">
        <v-textarea :model-value="props.repositoryForm.description" label="Description" density="compact"
          variant="outlined" rows="2" auto-grow @update:model-value="updateRepositoryFormDescription" />
      </v-col>

      <v-col cols="12">
        <v-textarea :model-value="props.repositoryForm.authentication" label="Authentication" density="compact"
          variant="outlined" rows="2" auto-grow :required="props.requireAuthentication"
          @update:model-value="updateRepositoryFormAuthentication" />
      </v-col>
    </v-row>

    <div class="d-flex justify-end ga-2">
      <v-btn v-if="props.showCancelButton" variant="text" :disabled="props.submittingRepositoryForm"
        @click="emitCancelRepositoryForm">
        Cancel
      </v-btn>

      <v-btn color="primary" type="submit" :loading="props.submittingRepositoryForm" :disabled="!repositoryFormIsValid">
        {{ props.submitLabel }}
      </v-btn>
    </div>
  </v-form>
</template>
