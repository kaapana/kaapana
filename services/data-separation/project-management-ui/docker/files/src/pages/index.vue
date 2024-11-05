<template>
  <v-container max-width="1200">
    <v-row justify="space-between">
      <v-col cols="6">
        <h4 class="text-h4 py-8">Available Projects</h4>
      </v-col>
      <v-col cols="3" class="d-flex justify-end align-center">
        <v-btn block @click="projectDialog = true" size="large" prepend-icon="mdi-plus-box">
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
          <th class="text-left">
            Project ID
          </th>
          <th class="text-left">
            Name
          </th>
          <th class="text-left">
            Description
          </th>
          <th class="text-left">
            External ID
          </th>
          <th class="text-center">
            Action
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in projects" :key="item.name">
          <td><v-icon>mdi-folder-file</v-icon></td>
          <td>{{ item.id }}</td>
          <td class="project-name-col">{{ item.name }}</td>
          <td class="desc-col">{{ item.description }}</td>
          <td>{{ item.external_id }}</td>
          <td class="text-center">
            <v-btn 
              class="text-none" color="medium-emphasis" 
              min-width="92" variant="outlined" size="small" rounded
              append-icon="mdi-arrow-right"
              @click="goToProjects(item.name)">
              View
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
  </v-container>
  <v-dialog v-model="projectDialog" max-width="1000">
    <CreateNewProjectForm :onsuccess="handleProjectCreate" :oncancel="() => projectDialog = false" />
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import CreateNewProjectFrom from '@/components/CreateNewProjectForm.vue'
import { aiiApiGet } from '@/common/aiiApi.service';
import { ProjectItem, UserItem } from '@/common/types';
import store from '@/common/store';

export default defineComponent({
  components: {
    CreateNewProjectFrom
  },
  props: {},
  data() {
    return {
      projects: [] as ProjectItem[],
      projectDialog: false,
      error: false,
      projectFetched: false,
    }
  },
  mounted() {
    // Store watch not triggering for some reasom
    // Temporary solution to check for user via
    // custom interval loop
    const fetchProjectsRef = this.fetchProjects
    let checkForUser = setInterval(function() {
      const user = store.state.user;
      if (user) {
        fetchProjectsRef(user);
        clearInterval(checkForUser);
      }
    }, 100)
  },
  watch: {
    // TODO
    // Watching the user object deeply
    // not triggering
    'store.state.user': {
      handler(newValue, oldValue) {
        console.log('User object changed:', { newValue, oldValue });

        // Perform your logic here, e.g., fetching projects
        if (newValue !== oldValue) {
          this.fetchProjects(newValue);
        }
      },
      deep: true // Enables deep watching of user object
    }
  },
  methods: {
    fetchProjects: function (user: UserItem) {
      // console.log(user)
      // project url to fetch the projects under the user
      let projects_url = `users/${user.id}/projects`;

      // if default-user / super-admin, fetch all the projects
      if (user.username == 'kaapana') {
        projects_url = `projects`;
      }

      try {
        aiiApiGet(projects_url).then((projects: ProjectItem[]) => {
          this.projects = projects;
          this.projectFetched = true;
        })
      } catch (error: unknown) {
        console.log(error)
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
    goToProjects(projectName: string) {
      this.$router.push(`/project/${projectName}`);
    }
  },
})
</script>


<style scoped>
.project-name-col{
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 150px;
}
.desc-col{
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 350px;
}
</style>
