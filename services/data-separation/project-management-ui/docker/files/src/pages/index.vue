<template>
  <v-container fluid class="pm-view">
    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <h1 class="text-h4">Projects</h1>
      <div v-if="userHasAdminAccess" class="d-flex flex-wrap ga-2">
        <v-btn
          variant="outlined"
          :prepend-icon="projectIcons.roleRights"
          @click="$router.push('/role-rights')"
        >
          Edit Role Rights
        </v-btn>
        <v-btn color="primary" :prepend-icon="kaapanaIcons.add" @click="projectDialog = true">
          Create New Project
        </v-btn>
      </div>
    </div>

    <v-card :elevation="2">
      <v-toolbar color="surface-light" flat density="comfortable">
        <v-text-field
          v-model="search"
          :prepend-inner-icon="kaapanaIcons.search"
          label="Search projects"
          variant="outlined"
          density="compact"
          clearable
          hide-details
          class="mx-4 pm-search"
        />
      </v-toolbar>

      <v-divider />

      <div v-if="loadError" class="px-4 pb-4">
        <FailureAlert
          title="Projects not loaded"
          text="Could not load the projects."
          :error="loadError"
          :retry="fetchProjects"
        />
      </div>

      <v-data-table
        v-else
        :headers="tableHeaders"
        :items="projects"
        :search="search"
        :loading="loading"
        loading-text="Loading projects…"
        item-value="id"
        :items-per-page="-1"
        hide-default-footer
      >
        <template #no-data>
          <ListEmptyState
            :search="search"
            noun="projects"
            :title="userHasAdminAccess ? 'No projects yet' : 'You are not in any project yet'"
            :text="
              userHasAdminAccess
                ? 'Create the first project to give users a place for their data and workflows.'
                : 'Ask a project manager or a project\'s principal investigator to add you.'
            "
            @clear-search="search = ''"
          >
            <template v-if="userHasAdminAccess" #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.add"
                @click="projectDialog = true"
              >
                Create New Project
              </v-btn>
            </template>
          </ListEmptyState>
        </template>

        <template #item.name="{ item }">
          <span class="font-weight-medium">{{ item.name }}</span>
          <v-chip v-if="item.is_archived" size="x-small" color="warning" class="ml-2"
            >Archived</v-chip
          >
        </template>

        <template #item.description="{ item }">
          <span class="text-medium-emphasis text-body-2">{{ item.description }}</span>
        </template>

        <template #item.view="{ item }">
          <v-btn
            color="primary"
            variant="text"
            :append-icon="projectIcons.open"
            @click.stop="goToProjects(item.id)"
          >
            View
          </v-btn>
        </template>

        <template v-if="userHasAdminAccess" #item.actions="{ item }">
          <template v-if="item.name !== 'admin'">
            <v-tooltip v-if="!item.is_archived" text="Edit project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="kaapanaIcons.edit"
                  :aria-label="`Edit ${item.name}`"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="primary"
                  @click.stop="openEditDialog(item)"
                />
              </template>
            </v-tooltip>
            <v-tooltip v-if="!item.is_archived" text="Archive project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="projectIcons.archive"
                  :aria-label="`Archive ${item.name}`"
                  :loading="busy?.id === item.id && busy.action === 'archive'"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="primary"
                  @click.stop="openArchiveDialog(item)"
                />
              </template>
            </v-tooltip>
            <v-tooltip v-if="item.is_archived" text="Unarchive project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="projectIcons.unarchive"
                  :aria-label="`Unarchive ${item.name}`"
                  :loading="busy?.id === item.id && busy.action === 'unarchive'"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="primary"
                  @click.stop="unarchiveProject(item)"
                />
              </template>
            </v-tooltip>
            <v-tooltip text="Delete project" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="kaapanaIcons.delete"
                  :aria-label="`Delete ${item.name}`"
                  :loading="busy?.id === item.id && busy.action === 'delete'"
                  :disabled="busy !== null"
                  size="default"
                  variant="text"
                  color="error"
                  @click.stop="openDeleteDialog(item)"
                />
              </template>
            </v-tooltip>
          </template>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
  <v-dialog v-model="projectDialog" max-width="600">
    <CreateNewProjectForm
      v-if="projectDialog"
      @created="handleProjectCreated"
      @cancel="projectDialog = false"
    />
  </v-dialog>
  <v-dialog v-model="editDialog" max-width="600">
    <EditProjectDialog
      v-if="editDialog && selectedProject"
      :project="selectedProject"
      @success="handleEditSuccess"
      @cancel="editDialog = false"
    />
  </v-dialog>
  <ConfirmDialog
    v-model="confirmOpen"
    :color="confirmation.color"
    :title="confirmation.title"
    :text="confirmation.text"
    :confirm-text="confirmation.confirmText"
    @confirm="runConfirmed"
  />
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { notify } from '@kyvg/vue3-notification'
import { ConfirmDialog, refreshShell } from '@kaapana/base-ui'
import CreateNewProjectForm from '@/components/CreateNewProjectForm.vue'
import EditProjectDialog from '@/components/EditProjectDialog.vue'
import FailureAlert from '@/components/FailureAlert.vue'
import ListEmptyState from '@/components/ListEmptyState.vue'
import { aiiApiGet, aiiApiDelete, aiiApiPost } from '@/common/services'
import { ProjectItem, UserItem } from '@/common/types'
import { isAdminUser, waitForStoreUser } from '@/common/userAccess'
import { useConfirmation } from '@/composables/useConfirmation'
import { notifyFailure } from '@/utils/notifyFailure'
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { archiveProjectConfirmation, deleteProjectConfirmation } from '@/utils/projectConfirmations'

const router = useRouter()
const { confirmOpen, confirmation, ask, runConfirmed } = useConfirmation()

const user = ref<UserItem | null>(null)
const projects = ref<ProjectItem[]>([])
const search = ref('')
const loading = ref(false)
const loadError = ref<unknown>(null)
const userHasAdminAccess = computed(() => !!user.value && isAdminUser(user.value))

const projectDialog = ref(false)
const editDialog = ref(false)
const selectedProject = ref<ProjectItem | null>(null)
const busy = ref<{ id: string; action: 'delete' | 'archive' | 'unarchive' } | null>(null)

const tableHeaders = computed(() => {
  const base = [
    { title: 'Short ID', key: 'short_id', sortable: true },
    { title: 'Name', key: 'name', sortable: true },
    { title: 'Description', key: 'description', sortable: false },
  ]
  const adminOnly = [{ title: 'External ID', key: 'external_id', sortable: true }]
  const view = [{ title: 'View', key: 'view', sortable: false, align: 'center' as const }]
  const actions = [{ title: 'Actions', key: 'actions', sortable: false, align: 'center' as const }]
  return userHasAdminAccess.value
    ? [...base, ...adminOnly, ...view, ...actions]
    : [...base, ...view]
})

onMounted(() => {
  waitForStoreUser((currentUser) => {
    user.value = currentUser
    fetchProjects()
  })
})

async function fetchProjects() {
  if (!user.value) return
  const url = isAdminUser(user.value) ? 'projects' : `users/${user.value.id}/projects`
  loading.value = true
  loadError.value = null
  try {
    projects.value = await aiiApiGet(url)
  } catch (error) {
    loadError.value = error
  } finally {
    loading.value = false
  }
}

function handleProjectCreated() {
  projectDialog.value = false
  fetchProjects()
}

function goToProjects(projectId: string) {
  router.push(`/project/${projectId}`)
}

function openEditDialog(project: ProjectItem) {
  selectedProject.value = project
  editDialog.value = true
}

function handleEditSuccess() {
  editDialog.value = false
  refreshShell()
  fetchProjects()
  notify({ type: 'success', text: 'Project updated.' })
}

function openDeleteDialog(project: ProjectItem) {
  ask(deleteProjectConfirmation(project, () => deleteProject(project)))
}

async function deleteProject(project: ProjectItem) {
  busy.value = { id: project.id, action: 'delete' }
  try {
    await aiiApiDelete(`projects/${project.id}`)
    refreshShell()
    fetchProjects()
    notify({ type: 'success', text: `Project "${project.name}" deleted.` })
  } catch (error) {
    notifyFailure('Project not deleted', `Could not delete "${project.name}".`, error)
  } finally {
    busy.value = null
  }
}

function openArchiveDialog(project: ProjectItem) {
  ask(archiveProjectConfirmation(project, () => archiveProject(project)))
}

async function archiveProject(project: ProjectItem) {
  busy.value = { id: project.id, action: 'archive' }
  try {
    await aiiApiPost(`projects/${project.id}/archive`, {})
    refreshShell()
    fetchProjects()
    notify({ type: 'success', text: `Project "${project.name}" archived.` })
  } catch (error) {
    notifyFailure('Project not archived', `Could not archive "${project.name}".`, error)
  } finally {
    busy.value = null
  }
}

async function unarchiveProject(project: ProjectItem) {
  busy.value = { id: project.id, action: 'unarchive' }
  try {
    await aiiApiPost(`projects/${project.id}/unarchive`, {})
    refreshShell()
    fetchProjects()
    notify({ type: 'success', text: `Project "${project.name}" unarchived.` })
  } catch (error) {
    notifyFailure('Project not unarchived', `Could not unarchive "${project.name}".`, error)
  } finally {
    busy.value = null
  }
}
</script>

