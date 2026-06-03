<template>
  <v-snackbar v-model="showSnackbar" :timeout="3000" location="top" :color="snackbarColor" elevation="2" closable>
    {{ snackbarText }}
  </v-snackbar>
  <v-container max-width="1200" class="bg-surface rounded-lg mt-2">

    <!-- ── Header card ──────────────────────────────────────────── -->
    <v-row class="mb-4">
      <v-col>
        <v-sheet class="pa-4 rounded-lg" border>
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center ga-3">
              <v-icon icon="mdi-folder-multiple" color="primary" size="large" />
              <span class="text-h5 font-weight-bold">Available Projects</span>
            </div>
            <div v-if="userHasAdminAccess" class="d-flex ga-2">
              <v-btn size="large" variant="tonal" @click="$router.push('/role-rights')">
                <template #prepend><v-icon color="primary">mdi-shield-key</v-icon></template>
                Edit Role Rights
              </v-btn>
              <v-btn size="large" variant="tonal" @click="projectDialog = true">
                <template #prepend><v-icon color="primary">mdi-plus-box</v-icon></template>
                Create New Project
              </v-btn>
            </div>
          </div>
        </v-sheet>
      </v-col>
    </v-row>

    <v-alert density="compact" class="mb-4" v-model="error" icon="mdi-alert-circle"
      text="Some error happened while creating the project. Please try again with different inputs."
      title="Project could not be created" type="error" prominent closable />

    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      label="Search projects"
      clearable
      hide-details
      class="mb-3"
    />

    <v-data-table
      :headers="tableHeaders"
      :items="projects"
      :search="search"
      item-value="id"
      class="rounded-lg border"
    >
      <template #item.name="{ item }">
        <span class="text-subtitle-2" style="font-family: monospace">{{ item.name }}</span>
        <v-chip v-if="item.is_archived" size="x-small" color="warning" class="ml-2">Archived</v-chip>
      </template>

      <template #item.short_id="{ item }">
        <span style="font-family: monospace">{{ item.short_id }}</span>
      </template>

      <template #item.external_id="{ item }">
        <span style="font-family: monospace">{{ item.external_id }}</span>
      </template>

      <template #item.description="{ item }">
        <span class="text-medium-emphasis text-body-2">{{ item.description }}</span>
      </template>

      <template #item.view="{ item }">
        <v-btn class="text-none" color="primary" min-width="92" variant="outlined" size="small"
          append-icon="mdi-arrow-right" @click.stop="goToProjects(item.id)">
          View
        </v-btn>
      </template>

      <template v-if="userHasAdminAccess" #item.actions="{ item }">
        <template v-if="item.name !== 'admin'">
          <v-btn v-if="!item.is_archived" icon="mdi-pencil" size="default" variant="text" @click.stop="openEditDialog(item)" />
          <v-btn v-if="!item.is_archived" icon="mdi-archive-arrow-down" size="default" variant="text" color="warning" @click.stop="openArchiveDialog(item)" />
          <v-btn v-if="item.is_archived" icon="mdi-archive-arrow-up" size="default" variant="text" color="success" @click.stop="unarchiveItem(item)" />
          <v-btn icon="mdi-trash-can" size="default" variant="text" color="error" @click.stop="openDeleteDialog(item)" />
        </template>
      </template>

      <template #item.is_archived="{ item }">
        <span :class="{ 'opacity-60': item.is_archived }">{{ item.is_archived ? 'Yes' : '—' }}</span>
      </template>
    </v-data-table>

  </v-container>
  <v-dialog v-model="projectDialog" max-width="1000">
    <CreateNewProjectForm :onsuccess="handleProjectCreate" :oncancel="() => (projectDialog = false)" />
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
  <confirm ref="confirm"></confirm>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import CreateNewProjectFrom from "@/components/CreateNewProjectForm.vue";
import Confirm from "@/components/Confirm.vue";
import EditProjectDialog from "@/components/EditProjectDialog.vue";
import DeleteProjectDialog from "@/components/DeleteProjectDialog.vue";
import ArchiveProjectDialog from "@/components/ArchiveProjectDialog.vue";
import { aiiApiGet, aiiApiDelete, aiiApiPost } from "@/common/services";
import { ProjectItem, UserItem } from "@/common/types";
import { isAdminUser, waitForStoreUser } from "@/common/userAccess";
import { useSnackbar } from "@/composables/useSnackbar";
import store from "@/common/store";

export default defineComponent({
  components: {
    CreateNewProjectFrom,
    Confirm,
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
      projectFetched: false,
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
        { title: 'Name', key: 'name', sortable: true },
        { title: 'Description', key: 'description', sortable: false },
      ];
      const adminOnly = [
        { title: 'Short ID', key: 'short_id', sortable: true },
        { title: 'External ID', key: 'external_id', sortable: true },
      ];
      const view = [{ title: 'View', key: 'view', sortable: false, align: 'center' as const }];
      const actions = [{ title: 'Actions', key: 'actions', sortable: false, align: 'center' as const }];
      return this.userHasAdminAccess
        ? [...adminOnly.slice(0, 1), ...base, ...adminOnly.slice(1), ...view, ...actions]
        : [...base, ...view];
    },
  },
  watch: {
    // TODO
    // Watching the user object deeply
    // not triggering
    "store.state.user": {
      handler(newValue, oldValue) {
        // console.log("User object changed:", { newValue, oldValue });
        // Perform your logic here, e.g., fetching projects
        if (newValue !== oldValue) {
          this.fetchProjects(newValue);
        }
      },
      deep: true, // Enables deep watching of user object
    },
  },
  methods: {
    fetchProjects: function (user: UserItem) {
      // console.log(user)
      // project url to fetch the projects under the user
      let projects_url = `users/${user.id}/projects`;

      // if default-user / kaapana_admin, fetch all the projects
      if (user.realm_roles && user.realm_roles.includes("project-manager")) {
        projects_url = `projects`;
      }

      try {
        aiiApiGet(projects_url).then((projects: ProjectItem[]) => {
          this.projects = projects;
          this.projectFetched = true;
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

