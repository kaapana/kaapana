<template>
  <v-container max-width="1200">
    <v-row justify="space-between">
      <v-col cols="6">
        <h4 class="text-h4 py-8">Available Projects</h4>
      </v-col>
      <v-col cols="3" class="d-flex justify-end align-center">
        <v-btn block
          @click="projectDialog = true" 
          size="large"
          prepend-icon="mdi-plus-box"
        >
          Create New Projects
        </v-btn>
      </v-col>
    </v-row>
    <v-table>
      <thead>
        <tr>
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
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in projects" :key="item.name">
          <td>{{ item.id }}</td>
          <td>{{ item.name }}</td>
          <td>{{ item.description }}</td>
          <td>{{ item.external_id }}</td>
        </tr>
      </tbody>
    </v-table>
  </v-container>
  <v-dialog v-model="projectDialog" max-width="1000">
    <CreateNewProjectForm :onsuccess="handleProjectCreate" :oncancel="() => projectDialog = false"/>
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import CreateNewProjectFrom from '@/components/CreateNewProjectForm.vue'
import { aiiApiGet } from '@/common/aiiApi.service';

type ProjectItem = {
  id: number,
  external_id?: number,
  name: string,
  description?: string,
}

export default defineComponent({
  components: {
    CreateNewProjectFrom
  },
  props: {},
  data() {
    return {
      projects: [] as ProjectItem[],
      projectDialog: false,
    }
  },
  mounted() {
    this.fetchProjects()
  },
  methods: {
    fetchProjects: function() {
      try {
        aiiApiGet('projects').then((projects: ProjectItem[]) => {
          this.projects = projects
        })
      } catch (error: unknown) {
        console.log(error)
      }
    },
    handleProjectCreate: function() {
      this.fetchProjects();
      this.projectDialog = false;
    }
  }
})
</script>
