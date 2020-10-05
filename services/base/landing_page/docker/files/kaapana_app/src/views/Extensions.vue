<template lang="pug">
.workflow-applications
  v-container(grid-list-lg, text-left)
    div
      v-data-table.elevation-1(
        :headers="headers",
        :items="launchedAppLinks",
        :items-per-page="20",
        :loading="loading",
        loading-text="Waiting a few seconds..."
      )
        template(v-slot:item.releaseMame="{ item }")
          span {{ item.releaseMame }} &nbsp;
            a(:href='link', target='_blank' v-for="link in item.links" :key="item.link")
              v-icon(color='primary') mdi-open-in-new
        template(v-slot:item.successful="{ item }")
          v-icon(v-if="item.successful==='yes'" color='green') mdi-check-circle
          v-icon(v-if="item.successful==='no'" color='red') mdi-alert-circle
        template(v-slot:item.kind="{ item }")
          v-tooltip(bottom='' v-if="item.kind==='dag'")
            template(v-slot:activator='{ on, attrs }')
              v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                | mdi-chart-timeline-variant
            span A workflow or algorithm that will be added to Airflow DAGs
          v-tooltip(bottom='' v-if="item.kind==='extension'")
            template(v-slot:activator='{ on, attrs }')
              v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                | mdi-laptop
            span An application to work with
        template(v-slot:item.installed="{ item }")
          v-btn(
            @click="deleteChart(item.releaseMame, item.name, item.version, item.keywords)",
            color="primary",
             v-if="item.installed==='yes'"
          ) Uninstall
          v-btn(
            @click="installChart(item.name, item.version, item.keywords)",
            color="primary",
            v-if="item.installed==='no'"
          ) Install
</template>

<script lang="ts">
import Vue from "vue";
import request from "@/request";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

export default Vue.extend({
  data: () => ({
    loading: true,
    launchedAppLinks: [] as any,
    headers: [
      {
        text: "Name",
        align: "start",
        value: "releaseMame",
      },
      {
        text: "Version",
        align: "start",
        value: "version",
      },
      {
        text: "Kind",
        align: "start",
        value: "kind",
      },
      {
        text: "Description",
        align: "start",
        value: "description",
      },
      {
        text: "Helm Status",
        align: "start",
        value: "helm_status",
      },
      {
        text: "Kube Status",
        align: "start",
        value: "kube_status",
      },
      {
        text: "Ready",
        align: "start",
        value: "successful",
      },
      { text: "Action", value: "installed" },
    ],
  }),
  mounted() {
    this.loading = true;
    this.getHelmCharts();
    this.loading = false;
  },
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "commonData",
      "launchApplicationData",
      "availableApplications",
    ]),
  },
  methods: {
    getHelmCharts() {
      let params = {
        repo: "kaapana-public"
      };
      kaapanaApiService
        .helmApiGet("/extensions", params)
        .then((response: any) => {
          this.launchedAppLinks = response.data;
          this.loading = false;
        })
        .catch((err: any) => {
          this.loading = false;
          console.log(err);
        });
    },

    deleteChart(releaseName: any, name: any, version: any, keywords: any) {
      let params = {
        'release_name': releaseName
      }
      this.loading = true;
      kaapanaApiService
        .helmApiGet("/helm-delete-chart", params)
        .then((response: any) => {
          setTimeout(() => {
            this.getHelmCharts();
            //this.loading = false;
          }, 1000);
        })
        .catch((err: any) => {
          this.getHelmCharts();
          this.loading = false;
          console.log(err);
        });
    },

    installChart(name: any, version: any, keywords: any) {
      let payload = {
        'name': name,
        'version': version,
        'keywords': keywords
      }
      this.loading = true;
      kaapanaApiService
        .helmApiPost("/helm-install-chart", payload)
        .then((response: any) => {
            setTimeout(() => {
              this.getHelmCharts();
            }, 3000);
        })
        .catch((err: any) => {
          this.getHelmCharts();
          this.loading = false;
          console.log(err);
        });
    },
  },
});
</script>

<style lang="scss">
a {  text-decoration: none;}
</style>
