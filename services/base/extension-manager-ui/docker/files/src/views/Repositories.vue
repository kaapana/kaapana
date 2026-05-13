<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createRepository,
  deleteRepository,
  fetchRepositories,
  updateRepository,
} from '@/api/repositories'
import NewRepository from '@/components/NewRepository.vue'
import RepositoryIterator from '@/components/RepositoryIterator.vue'
import SelectedRepository from '@/components/SelectedRepository.vue'
import type {
  CreateRepositoryRequest,
  Repository,
  RepositoryFormState,
  UpdateRepositoryRequest,
} from '@/types/schemas'

const repositories = ref<Repository[]>([])
const loadingRepositories = ref(false)
const repositoryError = ref<string | null>(null)
const selectedRepository = ref<Repository | null>(null)
const selectedRepositoryForm = ref<RepositoryFormState>(createEmptyRepositoryForm())
const createRepositoryForm = ref<RepositoryFormState>(createEmptyRepositoryForm())
const showingNewRepositoryDialog = ref(false)
const creatingRepository = ref(false)
const createRepositoryError = ref<string | null>(null)
const editingSelectedRepository = ref(false)
const updatingSelectedRepository = ref(false)
const deletingSelectedRepository = ref(false)
const repositoryActionError = ref<string | null>(null)

function createEmptyRepositoryForm(): RepositoryFormState {
  return {
    name: '',
    description: '',
    repository_url: '',
    authentication: '',
  }
}

function createRepositoryFormFromRepository(
  repository: Repository,
): RepositoryFormState {
  return {
    name: repository.name,
    description: repository.description ?? '',
    repository_url: repository.repository_url,
    authentication: '',
  }
}

function createCreateRepositoryRequest(
  repositoryForm: RepositoryFormState,
): CreateRepositoryRequest {
  return {
    name: repositoryForm.name.trim(),
    description: repositoryForm.description.trim() || undefined,
    repository_url: repositoryForm.repository_url.trim(),
    authentication: repositoryForm.authentication.trim(),
  }
}

function createUpdateRepositoryRequest(
  repositoryForm: RepositoryFormState,
): UpdateRepositoryRequest {
  return {
    name: repositoryForm.name.trim(),
    description: repositoryForm.description.trim() || undefined,
    repository_url: repositoryForm.repository_url.trim(),
    authentication: repositoryForm.authentication.trim() || undefined,
  }
}

function updateSelectedRepositoryFromList() {
  if (!selectedRepository.value) return

  selectedRepository.value = repositories.value.find(
    (repository) => repository.id === selectedRepository.value?.id,
  ) ?? null
}

function selectRepository(repository: Repository) {
  selectedRepository.value = repository
  selectedRepositoryForm.value = createRepositoryFormFromRepository(repository)
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

  selectedRepositoryForm.value = createRepositoryFormFromRepository(
    selectedRepository.value,
  )
  editingSelectedRepository.value = true
  repositoryActionError.value = null
}

function cancelEditSelectedRepository() {
  editingSelectedRepository.value = false
  repositoryActionError.value = null
}

function showNewRepositoryDialog() {
  createRepositoryForm.value = createEmptyRepositoryForm()
  createRepositoryError.value = null
  showingNewRepositoryDialog.value = true
}

function clearNewRepositoryDialog() {
  if (creatingRepository.value) return

  showingNewRepositoryDialog.value = false
  createRepositoryForm.value = createEmptyRepositoryForm()
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
    updateSelectedRepositoryFromList()
  } catch (err) {
    console.error(err)
    repositoryError.value = 'Failed to fetch repositories.'
    repositories.value = []
  } finally {
    loadingRepositories.value = false
  }
}

async function createNewRepository() {
  creatingRepository.value = true
  createRepositoryError.value = null

  try {
    await createRepository(createCreateRepositoryRequest(createRepositoryForm.value))
    showingNewRepositoryDialog.value = false
    createRepositoryForm.value = createEmptyRepositoryForm()
    await loadRepositories()
  } catch (err) {
    console.error(err)
    createRepositoryError.value = 'Failed to create repository.'
  } finally {
    creatingRepository.value = false
  }
}

async function updateSelectedRepository() {
  if (!selectedRepository.value) return

  updatingSelectedRepository.value = true
  repositoryActionError.value = null

  try {
    selectedRepository.value = await updateRepository(
      selectedRepository.value.id,
      createUpdateRepositoryRequest(selectedRepositoryForm.value),
    )
    selectedRepositoryForm.value = createRepositoryFormFromRepository(
      selectedRepository.value,
    )
    editingSelectedRepository.value = false
    await loadRepositories()
  } catch (err) {
    console.error(err)
    repositoryActionError.value = 'Failed to update repository.'
  } finally {
    updatingSelectedRepository.value = false
  }
}

async function deleteSelectedRepository() {
  if (!selectedRepository.value) return

  deletingSelectedRepository.value = true
  repositoryActionError.value = null

  try {
    await deleteRepository(selectedRepository.value.id)
    clearSelectedRepository()
    await loadRepositories()
  } catch (err) {
    console.error(err)
    repositoryActionError.value = 'Failed to remove repository.'
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
          <v-btn variant="text" to="/catalog">
            <v-icon start>mdi-arrow-left</v-icon>
            Back to catalog
          </v-btn>

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

      <NewRepository :showing-new-repository-dialog="showingNewRepositoryDialog"
        :create-repository-form="createRepositoryForm" :creating-repository="creatingRepository"
        :create-repository-error="createRepositoryError" @clear-new-repository-dialog="clearNewRepositoryDialog"
        @update:create-repository-form="updateCreateRepositoryForm" @create-new-repository="createNewRepository" />

      <SelectedRepository :selected-repository="selectedRepository" :selected-repository-form="selectedRepositoryForm"
        :editing-selected-repository="editingSelectedRepository"
        :updating-selected-repository="updatingSelectedRepository"
        :deleting-selected-repository="deletingSelectedRepository" :repository-action-error="repositoryActionError"
        @clear-selected-repository="clearSelectedRepository"
        @enable-edit-selected-repository="enableEditSelectedRepository"
        @cancel-edit-selected-repository="cancelEditSelectedRepository"
        @update:selected-repository-form="updateSelectedRepositoryForm"
        @update-selected-repository="updateSelectedRepository" @delete-selected-repository="deleteSelectedRepository" />

      <RepositoryIterator :repositories="repositories" :loading-repositories="loadingRepositories"
        :repository-error="repositoryError" @select-repository="selectRepository" />
    </v-container>
  </v-container>
</template>
