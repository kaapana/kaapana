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
        <tr v-for="item in projects" :key="item.name">
          <td><v-icon>mdi-card</v-icon></td>
          <td>{{ item.id }}</td>
          <td>{{ item.short_id }}</td>
          <td class="project-name-col">{{ item.name }}</td>
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
                  <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEditDialog(item)" />
                  <v-btn icon="mdi-trash-can" size="small" variant="text" color="error" @click="confirmDeleteProject(item)" />
                </template>
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </v-table>
  </v-container>
  <v-dialog v-model="projectDialog" max-width="1000">
    <CreateNewProjectForm :onsuccess="handleProjectCreate" :oncancel="() => (projectDialog = false)" />
  </v-dialog>
  <v-dialog v-model="editDialog" max-width="600">
    <v-card title="Edit Project" prepend-icon="mdi-pencil">
      <v-card-text>
        <v-container>
          <v-row><v-col>
            <v-text-field v-model="editForm.name" label="Project Name" :rules="editNameRules" />
          </v-col></v-row>
          <v-row><v-col>
            <v-text-field v-model="editForm.description" label="Description" />
          </v-col></v-row>
          <v-row><v-col>
            <v-text-field v-model="editForm.external_id" label="External ID" />
          </v-col></v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="editDialog = false">Cancel</v-btn>
        <v-btn color="primary" variant="elevated" @click="submitEdit">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
  <confirm ref="confirm"></confirm>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import CreateNewProjectFrom from "@/components/CreateNewProjectForm.vue";
import Confirm from "@/components/Confirm.vue";
import { aiiApiGet, aiiApiPut, aiiApiDelete } from "@/common/aiiApi.service";
import { ProjectItem, UserItem } from "@/common/types";
import store from "@/common/store";

export default defineComponent({
  components: {
    CreateNewProjectFrom,
    Confirm,
  },
  props: {},
  data() {
    return {
      projects: [] as ProjectItem[],
      projectDialog: false,
      error: false,
      projectFetched: false,
      userHasAdminAccess: false,
      editDialog: false,
      selectedProject: null as ProjectItem | null,
      editForm: { name: '', description: '', external_id: '' },
      editNameRules: [
        (v: string) => !!v || 'Required.',
        (v: string) => v.length <= 13 || 'Max 13 characters',
        (v: string) => v === v.toLowerCase() || 'Only lowercase characters are supported',
        (v: string) => !v.includes(' ') || 'Spaces are not allowed',
        (v: string) => v !== 'admin' || 'Name "admin" is reserved',
      ],
      showSnackbar: false,
      snackbarText: '',
      snackbarColor: 'info',
    };
  },
  mounted() {
    // Store watch not triggering for some reasom
    // Temporary solution to check for user via
    // custom interval loop
    const fetchProjectsRef = this.fetchProjects;
    const setAdminAccessRef = this.setUserAdminAccess;
    let checkForUser = setInterval(function () {
      const user = store.state.user;
      if (user) {
        fetchProjectsRef(user);
        setAdminAccessRef(user);
        clearInterval(checkForUser);
      }
    }, 100);
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
    // enable the admin access of the user to be able to create new projects from the UI
    setUserAdminAccess(user: UserItem) {
      if (user.realm_roles && (user.realm_roles.includes('project-manager') || user.realm_roles.includes('admin'))) {
        this.userHasAdminAccess = true;
      }
    },
    goToProjects(projectId: string) {
      this.$router.push(`/project/${projectId}`);
    },
    openEditDialog(project: ProjectItem) {
      this.selectedProject = project;
      this.editForm = {
        name: project.name,
        description: project.description || '',
        external_id: project.external_id ? String(project.external_id) : '',
      };
      this.editDialog = true;
    },
    async submitEdit() {
      if (!this.selectedProject) return;
      const nameError = this.editNameRules.map(r => r(this.editForm.name)).find(r => r !== true);
      if (nameError) {
        this.snackbarText = String(nameError);
        this.snackbarColor = 'error';
        this.showSnackbar = true;
        return;
      }
      try {
        await aiiApiPut(`projects/${this.selectedProject.id}`, {}, {
          name: this.editForm.name,
          description: this.editForm.description,
          external_id: this.editForm.external_id || null,
        });
        this.editDialog = false;
        const user = store.state.user;
        if (user) this.fetchProjects(user);
        this.snackbarText = 'Project updated successfully.';
        this.snackbarColor = 'success';
        this.showSnackbar = true;
      } catch (error: unknown) {
        console.error(error);
        this.snackbarText = 'Failed to update project.';
        this.snackbarColor = 'error';
        this.showSnackbar = true;
      }
    },
    async confirmDeleteProject(project: ProjectItem) {
      // @ts-ignore
      if (await this.$refs.confirm.open('Delete Project', `Are you sure you want to delete "${project.name}"?`, { color: 'red' })) {
        try {
          await aiiApiDelete(`projects/${project.id}`);
          const user = store.state.user;
          if (user) this.fetchProjects(user);
          this.snackbarText = `Project "${project.name}" deleted.`;
          this.snackbarColor = 'success';
          this.showSnackbar = true;
        } catch (error: unknown) {
          console.error(error);
          this.snackbarText = 'Failed to delete project.';
          this.snackbarColor = 'error';
          this.showSnackbar = true;
        }
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
  width: 72px;
}
</style>
