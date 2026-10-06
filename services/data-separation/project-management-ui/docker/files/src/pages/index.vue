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

      <v-data-table :headers="tableHeaders" :items="projects" :search="search" item-value="id">
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
  <v-dialog v-model="projectDialog" max-width="1000">
    <CreateNewProjectForm :onsuccess="() => (projectDialog = false)" :oncomplete="handleProjectCreate" :oncancel="() => (projectDialog = false)" />
  </v-dialog>
  <v-dialog v-model="editDialog" max-width="600">
    <EditProjectDialog v-if="selectedProject" :project="selectedProject"
      @success="handleEditSuccess" @cancel="editDialog = false" @error="handleEditError" />
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

<script lang="ts">
import { kaapanaIcons, projectIcons } from '@/utils/projectIcons'
import { defineComponent } from 'vue'
import CreateNewProjectForm from '@/components/CreateNewProjectForm.vue'
import EditProjectDialog from '@/components/EditProjectDialog.vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { aiiApiGet, aiiApiDelete, aiiApiPost } from '@/common/services'
import { refreshShell } from '@/common/shell'
import { ProjectItem, UserItem } from '@/common/types'
import { isAdminUser, waitForStoreUser } from '@/common/userAccess'
import { notify } from '@kyvg/vue3-notification'
import { notifyFailure } from '@/utils/notifyFailure'
import { useConfirmation } from '@/composables/useConfirmation'
import { archiveProjectConfirmation, deleteProjectConfirmation } from '@/utils/projectConfirmations'
import store from '@/common/store'

export default defineComponent({
  components: {
    CreateNewProjectForm,
    EditProjectDialog,
    ConfirmDialog,
  },
  props: {},
  setup() {
    const { confirmOpen, confirmation, ask, runConfirmed } = useConfirmation()
    return {
      kaapanaIcons,
      projectIcons,
      confirmOpen,
      confirmation,
      ask,
      runConfirmed,
    }
  },
  data() {
    return {
      projects: [] as ProjectItem[],
      search: '',
      projectDialog: false,
      userHasAdminAccess: false,
      editDialog: false,
      selectedProject: null as ProjectItem | null,
    };
  },
  mounted() {
    waitForStoreUser((user) => {
      this.fetchProjects(user);
      this.userHasAdminAccess = isAdminUser(user);
    });
  },
  computed: {
    tableHeaders(): object[] {
      const base = [
        { title: 'Short ID', key: 'short_id', sortable: true },
        { title: 'Name', key: 'name', sortable: true },
        { title: 'Description', key: 'description', sortable: false },
      ];
      const adminOnly = [
        { title: 'External ID', key: 'external_id', sortable: true },
      ];
      const view = [{ title: 'View', key: 'view', sortable: false, align: 'center' as const }];
      const actions = [{ title: 'Actions', key: 'actions', sortable: false, align: 'center' as const }];
      return this.userHasAdminAccess
        ? [...base, ...adminOnly, ...view, ...actions]
        : [...base, ...view];
    },
  },
  methods: {
    fetchProjects: function (user: UserItem) {
      let projects_url = `users/${user.id}/projects`;

      // if default-user / kaapana_admin, fetch all the projects
      if (user.realm_roles && user.realm_roles.includes("project-manager")) {
        projects_url = `projects`;
      }

      try {
        aiiApiGet(projects_url).then((projects: ProjectItem[]) => {
          this.projects = projects;
        });
      } catch (error: unknown) {
        console.log(error);
      }
    },
    handleProjectCreate: function (success: boolean = true, error?: unknown) {
      if (success) {
        const user = store.state.user;
        if (user) {
          this.fetchProjects(user);
        }
      } else {
        notifyFailure('Project not created', 'The project could not be created.', error)
      }
      this.projectDialog = false;
    },
    goToProjects(projectId: string) {
      this.$router.push(`/project/${projectId}`);
    },
    openEditDialog(project: ProjectItem) {
      this.selectedProject = project;
      this.editDialog = true;
    },
    handleEditSuccess() {
      this.editDialog = false
      refreshShell()
      const user = store.state.user
      if (user) this.fetchProjects(user)
      notify({ type: 'success', text: 'Project updated.' })
    },
    handleEditError(text: string, error?: unknown) {
      notifyFailure('Project not updated', text, error)
    },
    openDeleteDialog(project: ProjectItem) {
      this.ask(deleteProjectConfirmation(project, () => this.deleteProject(project)))
    },
    async deleteProject(project: ProjectItem) {
      try {
        await aiiApiDelete(`projects/${project.id}`)
        refreshShell()
        const user = store.state.user
        if (user) this.fetchProjects(user)
        notify({ type: 'success', text: `Project "${project.name}" deleted.` })
      } catch (error: unknown) {
        notifyFailure('Project not deleted', `Could not delete "${project.name}".`, error)
      }
    },
    openArchiveDialog(project: ProjectItem) {
      this.ask(archiveProjectConfirmation(project, () => this.archiveProject(project)))
    },
    async archiveProject(project: ProjectItem) {
      try {
        await aiiApiPost(`projects/${project.id}/archive`, {})
        refreshShell()
        const user = store.state.user
        if (user) this.fetchProjects(user)
        notify({ type: 'success', text: `Project "${project.name}" archived.` })
      } catch (error: unknown) {
        notifyFailure('Project not archived', `Could not archive "${project.name}".`, error)
      }
    },
    async unarchiveProject(project: ProjectItem) {
      try {
        await aiiApiPost(`projects/${project.id}/unarchive`, {})
        refreshShell()
        const user = store.state.user
        if (user) this.fetchProjects(user)
        notify({ type: 'success', text: `Project "${project.name}" unarchived.` })
      } catch (error: unknown) {
        notifyFailure('Project not unarchived', `Could not unarchive "${project.name}".`, error)
      }
    },
  },
});
</script>

