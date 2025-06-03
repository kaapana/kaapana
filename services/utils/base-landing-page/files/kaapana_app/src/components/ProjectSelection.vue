<template>
  <div>
    <v-list>
      <v-list-item-group v-model="selectedProject" color="primary">
        <v-list-item v-for="project in projects" :key="project.id" :value="project">
          <v-list-item-title
            :active="project.name === selectedProject"
            :disabled="project.name === selectedProject"
            >{{ project.name }}</v-list-item-title
          >
        </v-list-item>
      </v-list-item-group>
    </v-list>
  </div>
</template>

<script>
import { fetchProjects } from "../common/api.service";
import { UPDATE_SELECTED_PROJECT } from "@/store/actions.type";

export default {
  data() {
    return {
      projects: [],
      selectedProject: null,
    };
  },
  async mounted() {
    this.projects = await fetchProjects();
  },
  watch: {
    selectedProject(newProject) {
      if (newProject) {
        this.$store.dispatch(UPDATE_SELECTED_PROJECT, newProject);
      }
    },
  },
};
</script>

<style scoped>
/* Add any necessary styling here */
</style>
