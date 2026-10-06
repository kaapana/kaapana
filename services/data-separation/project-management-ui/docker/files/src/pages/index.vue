<template>
  <v-snackbar v-model="showSnackbar" :timeout="6000" location="top" :color="snackbarColor" elevation="2">
    {{ snackbarText }}
  </v-snackbar>
  <v-container fluid class="pm-view">
    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <h1 class="text-h4">Projects</h1>
      <div v-if="userHasAdminAccess" class="d-flex flex-wrap ga-2">
        <v-btn
          variant="outlined"
          prepend-icon="mdi-shield-key"
          @click="$router.push('/role-rights')"
        >
          Edit Role Rights
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="projectDialog = true">
          Create New Project
        </v-btn>
      </div>
    </div>

    <v-alert density="compact" class="mb-4" v-model="error" icon="mdi-alert-circle"
      text="Some error happened while creating the project. Please try again with different inputs."
      title="Project could not be created" type="error" prominent closable />

    <v-card :elevation="2">
      <v-toolbar color="surface-light" flat density="comfortable">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
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
            append-icon="mdi-arrow-right"
            @click.stop="goToProjects(item.id)"
          >
            View
          </v-btn>
        </template>

        <template v-if="userHasAdminAccess" #item.actions="{ item }">
          <template v-if="item.name !== 'admin'">
            <v-btn
              v-if="!item.is_archived"
              icon="mdi-pencil"
              size="default"
              variant="text"
              color="primary"
              @click.stop="openEditDialog(item)"
            />
            <v-btn
              v-if="!item.is_archived"
              icon="mdi-archive-arrow-down"
              size="default"
              variant="text"
              color="primary"
              @click.stop="openArchiveDialog(item)"
            />
            <v-btn
              v-if="item.is_archived"
              icon="mdi-archive-arrow-up"
              size="default"
              variant="text"
              color="primary"
              @click.stop="unarchiveItem(item)"
            />
            <v-btn
              icon="mdi-trash-can"
              size="default"
              variant="text"
              color="error"
              @click.stop="openDeleteDialog(item)"
            />
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
  <v-dialog v-model="deleteDialog" max-width="500">
    <DeleteProjectDialog v-if="selectedProject" :project="selectedProject"
      @confirm="handleDeleteConfirm" @cancel="deleteDialog = false" />
  </v-dialog>
  <v-dialog v-model="archiveDialog" max-width="560">
    <ArchiveProjectDialog v-if="selectedProject" :project="selectedProject"
      @confirm="handleArchiveConfirm" @cancel="archiveDialog = false" />
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import CreateNewProjectForm from "@/components/CreateNewProjectForm.vue";
import EditProjectDialog from "@/components/EditProjectDialog.vue";
import DeleteProjectDialog from "@/components/DeleteProjectDialog.vue";
import ArchiveProjectDialog from "@/components/ArchiveProjectDialog.vue";
import { aiiApiGet, aiiApiDelete, aiiApiPost } from "@/common/services";
import { refreshShell } from "@/common/shell";
import { ProjectItem, UserItem } from "@/common/types";
import { isAdminUser, waitForStoreUser } from "@/common/userAccess";
import { useSnackbar } from "@/composables/useSnackbar";
import store from "@/common/store";

export default defineComponent({
  components: {
    CreateNewProjectForm,
    EditProjectDialog,
    DeleteProjectDialog,
    ArchiveProjectDialog,
  },
  props: {},
  setup() {
    const { showSnackbar, snackbarText, snackbarColor, notify } = useSnackbar();
    return { showSnackbar, snackbarText, snackbarColor, notify };
  },
  data() {
    return {
      projects: [] as ProjectItem[],
      search: '',
      projectDialog: false,
      error: false,
      userHasAdminAccess: false,
      editDialog: false,
      deleteDialog: false,
      archiveDialog: false,
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
    handleProjectCreate: function (success: boolean = true) {
      if (success) {
        const user = store.state.user;
        if (user) {
          this.fetchProjects(user);
        }
      } else {
        this.error = true;
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
      this.editDialog = false;
      refreshShell();
      const user = store.state.user;
      if (user) this.fetchProjects(user);
      this.notify('Project updated successfully.', 'success');
    },
    handleEditError(msg: string) {
      this.notify(msg, 'error');
    },
    openDeleteDialog(project: ProjectItem) {
      this.selectedProject = project;
      this.deleteDialog = true;
    },
    async handleDeleteConfirm() {
      if (!this.selectedProject) return;
      const project = this.selectedProject;
      this.deleteDialog = false;
      try {
        await aiiApiDelete(`projects/${project.id}`);
        refreshShell();
        const user = store.state.user;
        if (user) this.fetchProjects(user);
        this.notify(`Project "${project.name}" deleted.`, 'success');
      } catch (error: unknown) {
        console.error(error);
        this.notify('Failed to delete project.', 'error');
      }
    },
    openArchiveDialog(project: ProjectItem) {
      this.selectedProject = project;
      this.archiveDialog = true;
    },
    async handleArchiveConfirm() {
      if (!this.selectedProject) return;
      const project = this.selectedProject;
      this.archiveDialog = false;
      try {
        await aiiApiPost(`projects/${project.id}/archive`, {});
        refreshShell();
        const user = store.state.user;
        if (user) this.fetchProjects(user);
        this.notify(`Project "${project.name}" archived.`, 'success');
      } catch (error: unknown) {
        console.error(error);
        this.notify('Failed to archive project.', 'error');
      }
    },
    async unarchiveItem(project: ProjectItem) {
      try {
        await aiiApiPost(`projects/${project.id}/unarchive`, {});
        refreshShell();
        const user = store.state.user;
        if (user) this.fetchProjects(user);
        this.notify(`Project "${project.name}" unarchived.`, 'success');
      } catch (error: unknown) {
        console.error(error);
        this.notify('Failed to unarchive project.', 'error');
      }
    },
  },
});
</script>

