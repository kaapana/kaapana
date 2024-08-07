<template>
  <div>
    <v-list>
      <v-list-item-group v-model="selectedProject" color="primary">
        <v-list-item v-for="project in projects" :key="project.id" :value="project">
          <v-list-item-title>{{ project.name }}</v-list-item-title>
        </v-list-item>
      </v-list-item-group>
    </v-list>
  </div>
</template>

<script>
import axios from "axios";
import httpClient from "../common/httpClient";

export default {
  data() {
    return {
      projects: [],
      selectedProject: null,
    };
  },
  mounted() {
    this.fetchProjects();
  },
  watch: {
    selectedProject(newProject) {
      console.log("newProject: " + newProject);
      localStorage.setItem("selectedProject", JSON.stringify(newProject));
      window.location.reload();
    },
  },
  methods: {
    setSelectedProject() {
      console.log(this.selectedProject.text);
      localStorage["selectedProject"] = this.selectedProject.text;
    },
    async fetchProjects() {
      try {
        const response = await httpClient.get("/aii/projects");
        this.projects = response.data;
      } catch (error) {
        console.error("Error fetching projects:", error);
      }
    },
  },
};
</script>

<style scoped>
/* Add any necessary styling here */
</style>
