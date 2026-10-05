<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  apiErrorInfo,
  apiErrorText,
  ConfirmDialog,
  kaapanaIcons,
  postViewDirty,
} from '@kaapana/base-ui'
import { fetchExtensions } from '@/features/extensions/api'
import {
  createRepository,
  deleteRepository,
  fetchRepositories,
  updateRepository,
} from '@/features/repositories/api'
import RepositoryFormDialog from '@/features/repositories/components/RepositoryFormDialog.vue'
import { toCreateRequest, toUpdateRequest } from '@/features/repositories/formAdapter'
import type { RepositoryFormState } from '@/features/repositories/types'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'
import { useFailureDetailsStore, type FailureDetails } from '@/shared/stores/failureDetails'
import type { InstalledExtension, Repository } from '@/shared/types/apiSchemas'
import { notifyFailure, notifySuccess } from '@/shared/utils/notify'
import { plural } from '@/shared/utils/status'

const failureDetails = useFailureDetailsStore()

const repositories = ref<Repository[]>([])
const installed = ref<InstalledExtension[]>([])
const loading = ref(false)
const loaded = ref(false)
const loadFailure = ref<FailureDetails | null>(null)

const formOpen = ref(false)
const formRepository = ref<Repository | null>(null)
const formSubmitting = ref(false)
const formFailure = ref<FailureDetails | null>(null)
const formDirty = ref(false)

const removeCandidate = ref<Repository | null>(null)
const showRemoveConfirm = ref(false)
const removingId = ref<string | null>(null)

watch(formDirty, (dirty) => postViewDirty(dirty))

const removeTitle = computed(() => `Remove repository "${removeCandidate.value?.name ?? ''}"?`)
const removeText = computed(() => {
  const repository = removeCandidate.value
  if (!repository) return ''
  const tracked = installed.value.filter(
    (extension) => extension.repository_id === repository.id && extension.status !== 'uninstalled',
  ).length
  const base =
    'Its extensions no longer appear in the catalog, and its stored credentials are deleted.'
  if (!tracked) return base
  return `${base} The extension manager also stops tracking the ${plural(tracked, 'extension')} installed from it: their content stays on the platform but can no longer be uninstalled here.`
})

function showLoadFailure() {
  if (loadFailure.value) failureDetails.show(loadFailure.value)
}

async function loadRepositories() {
  loading.value = true
  try {
    const [loadedRepositories, loadedExtensions] = await Promise.all([
      fetchRepositories(),
      fetchExtensions().catch(() => installed.value),
    ])
    repositories.value = loadedRepositories
    installed.value = loadedExtensions
    loadFailure.value = null
  } catch (err) {
    loadFailure.value = {
      title: repositories.value.length
        ? 'Could not refresh the repositories'
        : 'Could not load the repositories',
      text: 'The extension manager could not be reached or reported an error.',
      error: apiErrorInfo(err),
    }
  } finally {
    loading.value = false
    loaded.value = true
  }
}

function openCreateForm() {
  formRepository.value = null
  formFailure.value = null
  formOpen.value = true
}

function openEditForm(repository: Repository) {
  formRepository.value = repository
  formFailure.value = null
  formOpen.value = true
}

async function submitForm(form: RepositoryFormState) {
  const editing = formRepository.value
  formSubmitting.value = true
  formFailure.value = null
  try {
    if (editing) {
      const updated = await updateRepository(editing.id, toUpdateRequest(form))
      repositories.value = repositories.value.map((repository) =>
        repository.id === updated.id ? updated : repository,
      )
      notifySuccess('Repository saved', `The changes to "${updated.name}" are saved.`)
    } else {
      const created = await createRepository(toCreateRequest(form))
      repositories.value = [...repositories.value, created]
      notifySuccess(
        'Repository added',
        `"${created.name}" is registered. Its extensions appear in the catalog.`,
      )
    }
    formOpen.value = false
  } catch (err) {
    const fallback = editing
      ? `Could not save the changes to "${editing.name}".`
      : 'Could not add the repository.'
    formFailure.value = {
      title: editing ? 'Saving the repository failed' : 'Adding the repository failed',
      text: apiErrorText(err, fallback),
      error: apiErrorInfo(err),
    }
  } finally {
    formSubmitting.value = false
  }
}

function requestRemove(repository: Repository) {
  removeCandidate.value = repository
  showRemoveConfirm.value = true
}

async function removeRepository() {
  const repository = removeCandidate.value
  if (!repository || removingId.value) return
  removingId.value = repository.id
  try {
    await deleteRepository(repository.id)
    repositories.value = repositories.value.filter((entry) => entry.id !== repository.id)
    notifySuccess('Repository removed', `"${repository.name}" is no longer registered.`)
  } catch (err) {
    notifyFailure('Removing the repository failed', `Could not remove "${repository.name}".`, err)
  } finally {
    removingId.value = null
  }
}

onMounted(loadRepositories)
onBeforeUnmount(() => postViewDirty(false))
</script>

<template>
  <div>
    <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
      <div class="text-body-2 text-medium-emphasis">
        {{ plural(repositories.length, 'repository', 'repositories') }} registered
      </div>
      <div class="d-flex align-center ga-2">
        <v-btn
          variant="text"
          color="primary"
          :prepend-icon="kaapanaIcons.refresh"
          :loading="loading"
          :disabled="loading"
          @click="loadRepositories"
        >
          Refresh
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :prepend-icon="kaapanaIcons.add"
          data-testid="new-repository"
          @click="openCreateForm"
        >
          New repository
        </v-btn>
      </div>
    </div>

    <v-alert
      v-if="loadFailure && repositories.length"
      type="warning"
      variant="tonal"
      class="mb-4"
      data-testid="stale-alert"
    >
      Could not refresh the repositories. The list shows their last known state.
      <template #append>
        <v-btn variant="text" @click="showLoadFailure">Details</v-btn>
      </template>
    </v-alert>

    <BaseCardIterator
      :items="repositories"
      :loading="loading || !loaded"
      :item-key="(repository) => repository.id"
    >
      <template #card="{ item }">
        <v-card-title class="text-wrap">{{ item.name }}</v-card-title>
        <v-card-subtitle class="text-wrap">{{ item.repository_url }}</v-card-subtitle>
        <v-card-text
          class="flex-grow-1 text-body-2"
          :class="{ 'text-medium-emphasis': !item.description }"
        >
          {{ item.description || 'No description provided.' }}
        </v-card-text>
        <v-card-actions>
          <v-btn
            color="primary"
            variant="text"
            :prepend-icon="kaapanaIcons.edit"
            :aria-label="`Edit ${item.name}`"
            :disabled="removingId === item.id"
            @click="openEditForm(item)"
          >
            Edit
          </v-btn>
          <v-btn
            color="error"
            variant="text"
            :prepend-icon="kaapanaIcons.delete"
            :aria-label="`Remove ${item.name}`"
            :loading="removingId === item.id"
            :disabled="removingId === item.id"
            @click="requestRemove(item)"
          >
            Remove
          </v-btn>
        </v-card-actions>
      </template>

      <template #empty>
        <div data-testid="empty-state">
          <v-empty-state
            v-if="loadFailure"
            :icon="kaapanaIcons.error"
            color="error"
            size="56"
            title="Could not load the repositories"
            text="The extension manager could not be reached or reported an error. Try again, or contact your administrator if it persists."
          >
            <template #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.refresh"
                @click="loadRepositories"
              >
                Try again
              </v-btn>
              <v-btn variant="text" @click="showLoadFailure">Details</v-btn>
            </template>
          </v-empty-state>

          <v-empty-state
            v-else
            size="56"
            title="No repositories registered yet"
            text="Register the OCI repository your extensions are published to. Its extensions then appear in the catalog."
          >
            <template #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.add"
                @click="openCreateForm"
              >
                New repository
              </v-btn>
            </template>
          </v-empty-state>
        </div>
      </template>
    </BaseCardIterator>

    <RepositoryFormDialog
      v-model="formOpen"
      :repository="formRepository"
      :submitting="formSubmitting"
      :failure="formFailure"
      @update:dirty="formDirty = $event"
      @submit="submitForm"
    />

    <ConfirmDialog
      v-model="showRemoveConfirm"
      color="error"
      :title="removeTitle"
      :text="removeText"
      confirm-text="Remove repository"
      @confirm="removeRepository"
    />
  </div>
</template>
