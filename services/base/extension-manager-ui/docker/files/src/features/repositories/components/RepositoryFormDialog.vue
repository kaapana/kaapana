<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ConfirmDialog, kaapanaIcons } from '@kaapana/base-ui'
import { createFormState } from '@/features/repositories/formAdapter'
import type { RepositoryFormState } from '@/features/repositories/types'
import { useFailureDetailsStore, type FailureDetails } from '@/shared/stores/failureDetails'
import type { Repository } from '@/shared/types/apiSchemas'

type FieldRule = (value: string) => boolean | string

const props = defineProps<{
  modelValue: boolean
  repository: Repository | null
  submitting: boolean
  failure: FailureDetails | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'update:dirty', value: boolean): void
  (event: 'submit', form: RepositoryFormState): void
}>()

const failureDetails = useFailureDetailsStore()

const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const form = ref<RepositoryFormState>(createFormState())
const initialForm = ref<RepositoryFormState>(createFormState())
const showDiscardConfirm = ref(false)
let opener: HTMLElement | null = null

const editing = computed(() => props.repository !== null)
const title = computed(() =>
  props.repository ? `Edit repository "${props.repository.name}"` : 'New repository',
)
const submitLabel = computed(() => (editing.value ? 'Save changes' : 'Add repository'))

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    initialForm.value = createFormState(props.repository)
    form.value = { ...initialForm.value }
  },
  { immediate: true },
)

const isDirty = computed(
  () => props.modelValue && JSON.stringify(form.value) !== JSON.stringify(initialForm.value),
)
watch(isDirty, (dirty) => emit('update:dirty', dirty), { immediate: true })

const nameRules: FieldRule[] = [
  (value) => Boolean(value.trim()) || 'Enter a name. It identifies the repository in the catalog.',
]

const repositoryUrlRules: FieldRule[] = [
  (value) => Boolean(value.trim()) || 'Enter the repository URL.',
  (value) =>
    /^https?:\/\/\S+\/\S+$/i.test(value.trim()) ||
    'Use a full URL: http(s)://<registry>/<repository>, for example https://registry.example.com/group/repository.',
]

const usernameRules = computed<FieldRule[]>(() =>
  editing.value
    ? [
        (value) =>
          Boolean(value.trim()) ||
          !form.value.password ||
          'Enter the username too, or clear the password to keep the stored credentials.',
      ]
    : [(value) => Boolean(value.trim()) || 'Enter the username or token name for the registry.'],
)

const passwordRules = computed<FieldRule[]>(() =>
  editing.value
    ? [
        (value) =>
          Boolean(value) ||
          !form.value.username.trim() ||
          'Enter the password too, or clear the username to keep the stored credentials.',
      ]
    : [(value) => Boolean(value) || 'Enter the password or access token for the registry.'],
)

function close() {
  emit('update:modelValue', false)
  opener?.focus?.()
  opener = null
}

function requestClose() {
  if (props.submitting) return
  if (isDirty.value) {
    showDiscardConfirm.value = true
    return
  }
  close()
}

async function submit() {
  if (props.submitting) return
  const result = await formRef.value?.validate()
  if (result && !result.valid) return
  emit('submit', { ...form.value })
}

function showFailure() {
  if (props.failure) failureDetails.show(props.failure)
}
</script>

<template>
  <v-dialog
    :model-value="props.modelValue"
    max-width="600"
    scrollable
    @update:model-value="(value: boolean) => !value && requestClose()"
  >
    <v-card :elevation="5">
      <v-card-title class="d-flex align-start ga-2">
        <div class="flex-grow-1 text-wrap">
          <div class="text-h6">{{ title }}</div>
          <div class="text-body-2 text-medium-emphasis">
            {{
              editing
                ? 'Change how the platform reaches this OCI repository.'
                : 'Register an OCI repository to browse and install its extensions.'
            }}
          </div>
        </div>
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          aria-label="Close"
          @click="requestClose"
        />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert
          v-if="props.failure"
          type="error"
          variant="tonal"
          density="compact"
          class="mb-4"
          data-testid="form-failure"
        >
          {{ props.failure.text }}
          <template #append>
            <v-btn variant="text" size="small" @click="showFailure">Details</v-btn>
          </template>
        </v-alert>

        <v-form ref="formRef" @submit.prevent="submit">
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="form.name"
                :rules="nameRules"
                label="Name"
                density="compact"
                variant="outlined"
              />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="form.repository_url"
                :rules="repositoryUrlRules"
                label="Repository URL"
                density="compact"
                variant="outlined"
              />
            </v-col>
            <v-col cols="12">
              <v-textarea
                v-model="form.description"
                label="Description (optional)"
                density="compact"
                variant="outlined"
                rows="2"
                auto-grow
              />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="form.username"
                :rules="usernameRules"
                label="Username"
                density="compact"
                variant="outlined"
                autocomplete="off"
                :hint="
                  editing
                    ? 'Leave username and password empty to keep the stored credentials.'
                    : undefined
                "
                :persistent-hint="editing"
              />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="form.password"
                :rules="passwordRules"
                label="Password or access token"
                density="compact"
                variant="outlined"
                type="password"
                autocomplete="new-password"
              />
            </v-col>
          </v-row>

          <div class="d-flex justify-end ga-2 mt-4">
            <v-btn variant="text" :disabled="props.submitting" @click="requestClose">Cancel</v-btn>
            <v-btn
              color="primary"
              variant="flat"
              type="submit"
              :loading="props.submitting"
              :disabled="props.submitting"
            >
              {{ submitLabel }}
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="showDiscardConfirm"
    color="error"
    :title="editing ? 'Discard your changes to the repository?' : 'Discard the new repository?'"
    :text="
      editing
        ? 'The changes you made in this form will be lost. The repository keeps its saved settings.'
        : 'The values you entered will be lost. No repository is added.'
    "
    confirm-text="Discard changes"
    cancel-text="Keep editing"
    @confirm="close"
  />
</template>
