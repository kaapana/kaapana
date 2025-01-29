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
          :items="launchedAppLinks",
          :items-per-page="20",
          :loading="loading",
          sort-by='releaseName',
          loading-text="Loading applications..."
        )
          template(v-slot:item.links="{ item }")
            span {{ item.releaseName }} &nbsp;
              a(:href='link', target='_blank' v-for="link in item.links" :key="item.link")
                v-icon(color='primary') mdi-open-in-new
          template(v-slot:item.successful="{ item }")
            v-icon(v-if="item.successful==='yes'" color='green') mdi-check-circle
            v-icon(v-if="item.successful==='no'" color='red') mdi-alert-circle
          template(v-slot:item.releaseName="{ item }")
            v-btn(
              @click="deleteChart(item.releaseName)",
              color="primary",
            ) Complete interaction

      v-card
        v-card-title Applications installed in project: {{ selectedProject.name }}
        v-data-table.elevation-1(
          :headers="activeHeaders",
          :items="filteredActiveApplicationInProject",
          :items-per-page="20",
          :loading="loadingProject",
          sort-by='name',
          loading-text="Loading applications..."
        )
          template(v-slot:item.name="{ item }")
            span {{ item.name }} &nbsp;
            a(:href="item.url" target="_blank")
              v-icon(color='primary') mdi-open-in-new
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
    loading: true,
    loadingProject: true,
    launchedAppLinks: [] as any,
    projectApplications: [] as any,
    search: "",
    headers: [
      {
        text: "Name",
        align: "start",
        value: "links",
      },
      {
        text: "Helm Status",
        align: "start",
        value: "helmStatus",
      },
      {
        text: "Kube Status",
        align: "start",
        value: "kubeStatus",
      },
      {
        text: "Ready",
        align: "start",
        value: "successful",
      },
      { text: "Action", value: "releaseName" },
    ],
    activeHeaders: [{ text: "Name", value: "name" }],
  }),
  mounted() {
    this.getHelmCharts();
    this.getTraefikRoutes();
  },
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "commonData",
    ]),
    selectedProject() {
      return this.$store.getters.selectedProject;
    },
    filteredActiveApplicationInProject(){
      /**
       * Instead of using projectApplications to show the active projects display a filteredActiveApplicationsinProject
       *
       * Filters the list of project applications based on the launched application links.
       * 
       * This function checks if there are any launched application links (`launchedAppLinks`).
       * If there are links, it filters out the project applications (`projectApplications`) 
       * whose names match the `releaseName` of any launched link. This ensures that only 
       * applications not in the list of Applications triggered from a workflow.
       */
      const newLinks = this.launchedAppLinks;
      if (newLinks.length > 0) {
        const filteredProjectApps = this.projectApplications.filter((project: any) => {
          return newLinks.some((links: any) => {
            return links.releaseName !== project.name;
          });
        });
        return filteredProjectApps;
      } else {
        return this.projectApplications;
      }
    },
  },
  methods: {
    getHelmCharts() {
      kaapanaApiService
        .helmApiGet("/active-applications", {})
        .then((response: any) => {
          const launchedApps: Array<any> = response.data;
          const rulePattern = new RegExp(
            `^\/applications\/project\/${this.selectedProject.name}\/release\/.+$`
          );
          this.launchedAppLinks = launchedApps.filter((item: any) => {
            // check that all links for the application belong to the selected project.
            const applicationPaths: Array<string> = item.links;
            return applicationPaths.every((path: string) => {
              return rulePattern.test(path);
            });
          });

          this.loading = false;
        })
        .catch((err: any) => {
          this.loading = false;
          console.log(err);
        });
    },

    getTraefikRoutes() {
      kaapanaApiService
        .kaapanaApiGet("/get-traefik-routes")
        .then((response: any) => {
          // filter and format traefik routes
          this.projectApplications = response.data
            .filter((item: any) => {
              // sanity checks: items should be enabled, have a rule and a service
              if (item.status != "enabled") {
                return false;
              }
              if (!item.rule) {
                return false;
              }
              if (!item.service) {
                return false;
              }

              // check if the rule contains the required pattern for project namespace
              const rulePath = item.rule.slice(12, -2);
              const rulePattern = new RegExp(
                `^\/applications\/project\/${this.selectedProject.name}\/release\/.+$`
              );
              return rulePattern.test(rulePath);
            })
            .map((item: any) => {
              const url: string = item.rule.slice(12, -2).replace(RegExp("/\/+$/"), ""); // extract path from PathPrefix("<path>")
              const strippedUrl: string = url.replace(/\/+$/, "");
              const name: string = strippedUrl.substring(
                strippedUrl.lastIndexOf("/") + 1
              );
              return {
                name: name,
                url: url,
              };
            });
          this.loadingProject = false;
        })
        .catch((err: any) => {
          console.log(err);
          this.loadingProject = false;
        });
    },

    deleteChart(releaseName: any) {
      let params = {
        release_name: releaseName,
      };
      this.loading = true;
      kaapanaApiService
        .helmApiPost("/complete-active-application", params)
        .then((response: any) => {
          setTimeout(() => {
            this.getHelmCharts();
          }, 1000);
        })
        .catch((err: any) => {
          this.getHelmCharts();
          this.loading = false;
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
