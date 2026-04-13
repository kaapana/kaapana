<template>
  <v-snackbar v-model="showSnackbar" :timeout="6000" location="top" :color="snackbarColor" elevation="2">
    {{ snackbarText }}
  </v-snackbar>
  <v-container fluid class="px-6 py-0">
    <v-row justify="space-between" align="center">
      <v-col cols="auto">
        <h4 class="text-h4 py-6">Available Projects</h4>
      </v-col>
      <v-col cols="auto" v-if="userHasAdminAccess">
        <v-btn @click="projectDialog = true" size="large" prepend-icon="mdi-plus-box">
          Create New Projects
        </v-btn>
      </v-col>
    </v-row>

    <v-alert density="compact" class="mb-6" v-model="error" icon="mdi-alert-circle"
      text="Some error happened while creating the project. Please try again with different inputs."
      title="Project Could not be created" type="error" prominent closable></v-alert>

    <v-table>
      <thead>
        <tr>
          <th class="text-left"></th>
          <th class="text-left">Project UUID</th>
          <th class="text-left">Short ID</th>
          <th class="text-left">Name</th>
          <th class="text-left">Description</th>
          <th class="text-left">External ID</th>
          <th class="text-center">Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in projects" :key="item.id" :class="{ 'archived-row': item.is_archived }">
          <td><v-icon>mdi-card</v-icon></td>
          <td>{{ item.id }}</td>
          <td>{{ item.short_id }}</td>
          <td class="project-name-col">
            {{ item.name }}
            <v-chip v-if="item.is_archived" size="x-small" color="warning" class="ml-1">Archived</v-chip>
          </td>
          <td class="desc-col">{{ item.description }}</td>
          <td>{{ item.external_id }}</td>
          <td class="action-col">
            <div class="d-flex align-center justify-center" style="gap: 4px; flex-wrap: nowrap;">
              <v-btn class="text-none" color="medium-emphasis" min-width="92" variant="outlined" size="small" rounded
                append-icon="mdi-arrow-right" @click="goToProjects(item.id)">
                View
              </v-btn>
              <div v-if="userHasAdminAccess" class="icon-action-slot">
                <template v-if="item.name !== 'admin'">
                  <v-btn v-if="!item.is_archived" icon="mdi-pencil" size="small" variant="text" @click="openEditDialog(item)" />
                  <v-btn v-if="!item.is_archived" icon="mdi-archive-arrow-down" size="small" variant="text" color="warning" @click="openArchiveDialog(item)" />
                  <v-btn v-if="item.is_archived" icon="mdi-archive-arrow-up" size="small" variant="text" color="success" @click="unarchiveItem(item)" />
                  <v-btn icon="mdi-trash-can" size="small" variant="text" color="error" @click="openDeleteDialog(item)" />
                </template>
              </div>
            </div>
          </td>
        </tr>
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
import { aiiApiGet, aiiApiDelete, aiiApiPost } from "@/common/aiiApi.service";
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
    onRowClick(item: any, event: MouseEvent) {
      // If user is selecting text → DO NOT navigate
      const selection = window.getSelection();
      if (selection && selection.toString().length > 0) {
        return;
      }

      // If click originated from interactive element → ignore
      const target = event.target as HTMLElement;

      if (
        target.closest('button') ||
        target.closest('a') ||
        target.closest('.no-row-click')
      ) {
        return;
      }

      this.goToProjects(item.id);
    },
    goToProjects(projectId: string) {
      // Use name-based route for better URL readability
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

<style scoped>
.project-name-col {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}

.desc-col {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 350px;
}

.action-col {
  white-space: nowrap;
  text-align: center;
}

.icon-action-slot {
  display: inline-flex;
  gap: 4px;
  width: 108px;
}

.archived-row {
  opacity: 0.6;
}
</style>
