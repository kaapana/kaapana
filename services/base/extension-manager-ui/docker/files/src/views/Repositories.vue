<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createRepository,
  deleteRepository,
  fetchRepositories,
  updateRepository,
} from '@/features/repositories/api'
import NewRepository from '@/features/repositories/components/NewRepository.vue'
import RepositoryIterator from '@/features/repositories/components/RepositoryIterator.vue'
import SelectedRepository from '@/features/repositories/components/SelectedRepository.vue'
import {
  createFormState,
  toCreateRequest,
  toUpdateRequest,
} from '@/features/repositories/formAdapter'
import type { Repository } from '@/shared/types/apiSchemas'
import type { RepositoryFormState } from '@/features/repositories/types'
import { getApiErrorMessage } from '@/shared/utils/apiErrors'

const repositories = ref<Repository[]>([])
const loadingRepositories = ref(false)
const repositoryError = ref<string | null>(null)
const selectedRepository = ref<Repository | null>(null)
const selectedRepositoryForm = ref<RepositoryFormState>(createFormState())
const createRepositoryForm = ref<RepositoryFormState>(createFormState())
const showingNewRepositoryDialog = ref(false)
const creatingRepository = ref(false)
const createRepositoryError = ref<string | null>(null)
const editingSelectedRepository = ref(false)
const updatingSelectedRepository = ref(false)
const deletingSelectedRepository = ref(false)
const repositoryActionError = ref<string | null>(null)

function replaceRepositoryInList(updated: Repository) {
  const index = repositories.value.findIndex((repo) => repo.id === updated.id)
  if (index === -1) {
    repositories.value.push(updated)
  } else {
    repositories.value.splice(index, 1, updated)
  }
}

function selectRepository(repository: Repository) {
  selectedRepository.value = repository
  selectedRepositoryForm.value = createFormState(repository)
  editingSelectedRepository.value = false
  repositoryActionError.value = null
}

function clearSelectedRepository() {
  selectedRepository.value = null
  editingSelectedRepository.value = false
  repositoryActionError.value = null
}

function enableEditSelectedRepository() {
  if (!selectedRepository.value) return

  selectedRepositoryForm.value = createFormState(selectedRepository.value)
  editingSelectedRepository.value = true
  repositoryActionError.value = null
}

function cancelEditSelectedRepository() {
  editingSelectedRepository.value = false
  repositoryActionError.value = null
}

function showNewRepositoryDialog() {
  createRepositoryForm.value = createFormState()
  createRepositoryError.value = null
  showingNewRepositoryDialog.value = true
}

function clearNewRepositoryDialog() {
  if (creatingRepository.value) return

  showingNewRepositoryDialog.value = false
  createRepositoryForm.value = createFormState()
  createRepositoryError.value = null
}

function updateCreateRepositoryForm(repositoryForm: RepositoryFormState) {
  createRepositoryForm.value = repositoryForm
}

function updateSelectedRepositoryForm(repositoryForm: RepositoryFormState) {
  selectedRepositoryForm.value = repositoryForm
}

async function loadRepositories() {
  loadingRepositories.value = true
  repositoryError.value = null

  try {
    repositories.value = await fetchRepositories()
    if (selectedRepository.value) {
      selectedRepository.value =
        repositories.value.find((repository) => repository.id === selectedRepository.value?.id) ??
        null
    }
  } catch (err) {
    console.error(err)
    repositoryError.value = getApiErrorMessage(err, 'Failed to fetch repositories.')
    repositories.value = []
  } finally {
    loadingRepositories.value = false
  }
}

async function createNewRepository() {
  creatingRepository.value = true
  createRepositoryError.value = null

  try {
    const created = await createRepository(toCreateRequest(createRepositoryForm.value))
    repositories.value.push(created)
    showingNewRepositoryDialog.value = false
    createRepositoryForm.value = createFormState()
  } catch (err) {
    console.error(err)
    createRepositoryError.value = getApiErrorMessage(err, 'Failed to create repository.')
  } finally {
    creatingRepository.value = false
  }
}

async function updateSelectedRepository() {
  if (!selectedRepository.value) return

  updatingSelectedRepository.value = true
  repositoryActionError.value = null

  try {
    const updated = await updateRepository(
      selectedRepository.value.id,
      toUpdateRequest(selectedRepositoryForm.value),
    )
    replaceRepositoryInList(updated)
    selectedRepository.value = updated
    selectedRepositoryForm.value = createFormState(updated)
    editingSelectedRepository.value = false
  } catch (err) {
    console.error(err)
    repositoryActionError.value = getApiErrorMessage(err, 'Failed to update repository.')
  } finally {
    updatingSelectedRepository.value = false
  }
}

async function deleteSelectedRepository() {
  if (!selectedRepository.value) return

  deletingSelectedRepository.value = true
  repositoryActionError.value = null

  const idToDelete = selectedRepository.value.id

  try {
    await deleteRepository(idToDelete)
    repositories.value = repositories.value.filter((repo) => repo.id !== idToDelete)
    clearSelectedRepository()
  } catch (err) {
    console.error(err)
    repositoryActionError.value = getApiErrorMessage(err, 'Failed to remove repository.')
  } finally {
    deletingSelectedRepository.value = false
  }
}

onMounted(loadRepositories)
</script>

<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
        <div>
          <h1 class="text-h5 mb-1">Repository Management</h1>
          <div class="text-body-2 text-medium-emphasis">
            {{ repositories.length }} repositories registered
          </div>
        </div>

        <div class="d-flex align-center ga-2">
          <v-btn color="primary" variant="tonal" @click="showNewRepositoryDialog">
            <v-icon start>mdi-plus</v-icon>
            New repository
          </v-btn>

          <v-btn color="primary" :loading="loadingRepositories" @click="loadRepositories">
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </div>

      <NewRepository
        :showing-new-repository-dialog="showingNewRepositoryDialog"
        :create-repository-form="createRepositoryForm"
        :creating-repository="creatingRepository"
        :create-repository-error="createRepositoryError"
        @clear-new-repository-dialog="clearNewRepositoryDialog"
        @update:create-repository-form="updateCreateRepositoryForm"
        @create-new-repository="createNewRepository"
      />

      <SelectedRepository
        :selected-repository="selectedRepository"
        :selected-repository-form="selectedRepositoryForm"
        :editing-selected-repository="editingSelectedRepository"
        :updating-selected-repository="updatingSelectedRepository"
        :deleting-selected-repository="deletingSelectedRepository"
        :repository-action-error="repositoryActionError"
        @clear-selected-repository="clearSelectedRepository"
        @enable-edit-selected-repository="enableEditSelectedRepository"
        @cancel-edit-selected-repository="cancelEditSelectedRepository"
        @update:selected-repository-form="updateSelectedRepositoryForm"
        @update-selected-repository="updateSelectedRepository"
        @delete-selected-repository="deleteSelectedRepository"
      />

      <RepositoryIterator
        :repositories="repositories"
        :loading-repositories="loadingRepositories"
        :repository-error="repositoryError"
        @select-repository="selectRepository"
      />
    </v-container>
  </v-container>
</template>
