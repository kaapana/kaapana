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
            span If a DAG has started an application, the corresponding url will be listed here. Use 'Complete Interaction' button to continue the workflow.
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
          :items="projectApplications",
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
import Vue from 'vue';
import { mapGetters } from "vuex";
import kaapanaApiService from '@/common/kaapanaApi.service';
import IdleTracker from '@/components/IdleTracker.vue';

export default Vue.extend({
  components: {
    IdleTracker
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
    activeHeaders: [
      { text: "Name", value: "name" },
    ],
  }),
  mounted() {
    this.getHelmCharts();
    this.getTraefikRoutes();
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', "commonData", "launchApplicationData", "availableApplications", "selectedProject"])
  },
  methods: {
    getHelmCharts() {
      kaapanaApiService
        .helmApiGet("/pending-applications", {})
        .then((response: any) => {
          this.launchedAppLinks = response.data;
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
              const rulePattern = new RegExp(`^\/applications\/project\/${this.selectedProject.name}\/release\/[^/]+$`);
              return rulePattern.test(rulePath);
            })
            .map((item: any) => {
              const url = item.rule.slice(12, -2) // extract path from PathPrefix("<path>")
              return {
                name: url.substring(url.lastIndexOf('/') + 1),
                url: url
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
        .helmApiPost("/helm-delete-chart", params)
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
    },
  }
})
</script>

<style lang="scss">
a {
  text-decoration: none;
}
</style>
