<template lang="pug">
  .workflow-applications
    IdleTracker
    v-container(grid-list-lg text-left fluid)
      v-card
        v-card-title
          | Applications triggered from a workflow &nbsp;
          v-tooltip(bottom='')
            template(v-slot:activator='{ on, attrs }')
              v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                | mdi-information-outline
            span If a workflow has started an application, you will find a link to it here. Use 'Complete Interaction' button to continue workflow.
          v-spacer
          v-text-field(v-model='search' append-icon='mdi-magnify' label='Search' single-line='' hide-details='')
        v-data-table.elevation-1(
          :headers="headers",
          :items="triggeredApplications",
          :items-per-page="20",
          :loading="loadingTriggered",
          sort-by='releaseName',
          loading-text="Loading applications..."
        )
          template(v-slot:item.paths="{ item }")
              a(
                :href="path",
                target="_blank",
                v-for="path in item.paths",
                :key="item.path"
              )
                v-icon(color="primary") mdi-open-in-new
          template(v-slot:item.ready="{ item }")
            v-icon(v-if="item.ready===true" color='green') mdi-check-circle
            v-icon(v-if="item.ready===false" color='red') mdi-alert-circle
          template(v-slot:item.releaseName="{ item }")
            v-btn(
              @click="deleteChart(item.releaseName)",
              color="primary",
            ) Complete interaction

      v-card
        v-card-title Applications installed in project: {{ this.$store.getters.selectedProject.name }}
        v-data-table.elevation-1(
          :headers="activeHeaders",
          :items="projectApplications",
          :items-per-page="20",
          :loading="loadingProject",
          sort-by='name',
          loading-text="Loading applications..."
        )
          template(v-slot:item.paths="{ item }")
            a(
              :href="path",
              target="_blank",
              v-for="path in item.paths",
              :key="item.path"
            )
              v-icon(color="primary") mdi-open-in-new
          template(v-slot:item.ready="{ item }")
            v-icon(v-if="item.ready===true" color='green') mdi-check-circle
            v-icon(v-if="item.ready===false" color='red') mdi-alert-circle
</template>

<script lang="ts">
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";
import IdleTracker from "@/components/IdleTracker.vue";

export default Vue.extend({
  components: {
    IdleTracker,
  },
  data: () => ({
    loadingTriggered: true,
    loadingProject: true,
    projectApplications: [] as any,
    triggeredApplications: [] as any,
    search: "",
    headers: [
      { text: "Name", align: "start", value: "name" },
      { text: "Links", align: "start", value: "paths" },
      { text: "Ready", align: "start", value: "ready" },
      { text: "Installed At", align: "start", value: "createdAt" },
      { text: "Action", value: "releaseName" },
    ],
    activeHeaders: [
      { text: "Name", align: "start", value: "name" },
      { text: "Links", align: "start", value: "paths" },
      { text: "Ready", align: "start", value: "ready" },
      { text: "Project", align: "start", value: "project" },
      { text: "Installed At", align: "start", value: "createdAt" },
    ],
  }),
  mounted() {
    this.getActiveApplications();
  },
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "commonData",
    ]),
  },
  methods: {
    getActiveApplications() {
      kaapanaApiService
        .helmApiGet("/active-applications", {})
        .then((response: any) => {
          // filter and format ingress routes
          const allActiveApplications = response.data
            .filter((item: any) => {
              // sanity check: ingress should have a path
              if (item.paths.length == 0) {
                console.log("WARNING: ignoring application without paths:", item);
                return false;
              }
              return true;
            })
            .map((item: any) => {
              let name = item.name;
              if ("kaapana.ai/display-name" in item.annotations) {
                name = item.annotations["kaapana.ai/display-name"];
              }
              // format the date
              const formattedDate = new Intl.DateTimeFormat('en-UK', {
                dateStyle: 'long',
                timeStyle: 'short',
              }).format(new Date(item.created_at));
              return {
                annotations: item.annotations,
                createdAt: formattedDate,
                fromWorkflowRun: item.from_workflow_run,
                name: name,
                paths: item.paths,
                project: item.project,
                ready: item.ready,
                releaseName: item.release_name,
              };
            });
          // get applications that are triggered from workflow runs
          this.triggeredApplications = allActiveApplications.filter((item: any) => {
            return item.fromWorkflowRun === true;
          });
          // get applications that are not triggered from a workflow run and includes current project name in all paths
          this.projectApplications = allActiveApplications.filter((item: any) => {
            const rulePattern = new RegExp(
              `^\/applications\/project\/${this.$store.getters.selectedProject.name}\/release\/.+$`
            );
            let hasProjectURL = item.paths.every((path: string) => {
              return rulePattern.test(path);
            });
            return hasProjectURL && (item.fromWorkflowRun === false);
          });
          this.loadingProject = false;
          this.loadingTriggered = false;
        })
        .catch((err: any) => {
          console.log(err);
          this.loadingProject = false;
          this.loadingTriggered = false;
        });
    },

    deleteChart(releaseName: any) {
      let params = {
        release_name: releaseName,
      };
      this.loadingTriggered = true;
      kaapanaApiService
        .helmApiPost("/complete-active-application", params)
        .then((response: any) => {
          setTimeout(() => {
            this.getActiveApplications();
          }, 1000);
        })
        .catch((err: any) => {
          this.getActiveApplications();
          this.loadingTriggered = false;
          console.log(err);
        });

      // project needs to be deleted from the already fetched project list after deleteing the chart.
      // update the project application list by deleting the application with release name.
      const filteredProjectApps = this.projectApplications.filter((project: any) => project.name !== releaseName);
      this.projectApplications = filteredProjectApps;
    },
  },
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}
</style>
