<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RepositoryFormState } from '@/features/repositories/types'

const props = defineProps<{
  repositoryForm: RepositoryFormState
  submittingRepositoryForm: boolean
  submitLabel: string
  requireCredentials: boolean
  showCancelButton?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:repositoryForm', repositoryForm: RepositoryFormState): void
  (event: 'submitRepositoryForm'): void
  (event: 'cancelRepositoryForm'): void
}>()

type FieldRule = (value: string) => boolean | string

const formRef = ref<HTMLFormElement | null>(null)
const isFormValid = ref<boolean | null>(null)

const requiredRule: FieldRule = (value) => Boolean(value?.trim()) || 'This field is required.'

const nameRules: FieldRule[] = [requiredRule]

const repositoryUrlRules: FieldRule[] = [
  requiredRule,
  (value) =>
    /^\S+\/\S+$/.test(value.trim()) ||
    'Use the form <registry>/<repository>, e.g. https://registry.example.com/group/repository.',
]

// In edit mode credentials are optional (leave blank to keep the stored ones).
const credentialRules = computed<FieldRule[]>(() => (props.requireCredentials ? [requiredRule] : []))

function getUpdatedRepositoryForm(
  repositoryFormUpdate: Partial<RepositoryFormState>,
): RepositoryFormState {
  return {
    ...props.repositoryForm,
    ...repositoryFormUpdate,
  }
}

function updateRepositoryFormName(value: unknown) {
  emit('update:repositoryForm', getUpdatedRepositoryForm({ name: String(value ?? '') }))
}

function updateRepositoryFormDescription(value: unknown) {
  emit('update:repositoryForm', getUpdatedRepositoryForm({ description: String(value ?? '') }))
}

function updateRepositoryFormUrl(value: unknown) {
  emit('update:repositoryForm', getUpdatedRepositoryForm({ repository_url: String(value ?? '') }))
}

function updateRepositoryFormUsername(value: unknown) {
  emit('update:repositoryForm', getUpdatedRepositoryForm({ username: String(value ?? '') }))
}

function updateRepositoryFormPassword(value: unknown) {
  emit('update:repositoryForm', getUpdatedRepositoryForm({ password: String(value ?? '') }))
}

async function submitRepositoryForm() {
  const result = await formRef.value?.validate()
  if (result && !result.valid) return

  emit('submitRepositoryForm')
}
</script>

<template>
  <v-form ref="formRef" v-model="isFormValid" @submit.prevent="submitRepositoryForm">
    <v-row dense>
      <v-col cols="12" md="6">
        <v-text-field
          :model-value="props.repositoryForm.name"
          :rules="nameRules"
          label="Name"
          density="compact"
          variant="outlined"
          @update:model-value="updateRepositoryFormName"
        />
      </v-col>

      <v-col cols="12" md="6">
        <v-text-field
          :model-value="props.repositoryForm.repository_url"
          :rules="repositoryUrlRules"
          label="Repository URL"
          density="compact"
          variant="outlined"
          @update:model-value="updateRepositoryFormUrl"
        />
      </v-col>

      <v-col cols="12">
        <v-textarea
          :model-value="props.repositoryForm.description"
          label="Description"
          density="compact"
          variant="outlined"
          rows="2"
          auto-grow
          @update:model-value="updateRepositoryFormDescription"
        />
      </v-col>

      <v-col cols="12" md="6">
        <v-text-field
          :model-value="props.repositoryForm.username"
          :rules="credentialRules"
          label="Username"
          density="compact"
          variant="outlined"
          @update:model-value="updateRepositoryFormUsername"
        />
      </v-col>

      <v-col cols="12" md="6">
        <v-text-field
          :model-value="props.repositoryForm.password"
          :rules="credentialRules"
          label="Password / Access token"
          density="compact"
          variant="outlined"
          type="password"
          @update:model-value="updateRepositoryFormPassword"
        />
      </v-col>
    </v-row>

    <div class="d-flex justify-end ga-2">
      <v-btn
        v-if="props.showCancelButton"
        variant="text"
        :disabled="props.submittingRepositoryForm"
        @click="emit('cancelRepositoryForm')"
      >
        Cancel
      </v-btn>

      <v-btn
        color="primary"
        type="submit"
        :loading="props.submittingRepositoryForm"
        :disabled="isFormValid === false"
      >
        {{ props.submitLabel }}
      </v-btn>
    </div>
  </v-form>
</template>
