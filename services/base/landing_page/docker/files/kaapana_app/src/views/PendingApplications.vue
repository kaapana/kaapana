<template lang="pug">
  .workflow-applications
    v-container(grid-list-lg text-left)
      div
        h2 List of applications started in a workflow (max 2 applications at the same time)
        p If a workflow has started an application, you will find here the corresponding url to the application. Once you are done you can here finish the manual interaction which will continue the workflow.
        v-data-table.elevation-1(
          :headers="headers",
          :items="launchedAppLinks",
          :items-per-page="20",
          :loading="loading",
          loading-text="Waiting a few seconds..."
        )
          template(v-slot:item.link="{ item }")
            a(:href='item.link', target='_blank') {{ item.releaseMame }}
          template(v-slot:item.successful="{ item }")
            v-icon(v-if="item.successful==='yes'" color='green') mdi-check-circle
            v-icon(v-if="item.successful==='no'" color='red') mdi-alert-circle
          template(v-slot:item.releaseMame="{ item }")
            v-btn(
              @click="deleteChart(item.releaseMame)",
              color="primary",
            ) Finished manual interaction
</template>

<script lang="ts">
import Vue from 'vue';
import request from '@/request';
import { mapGetters } from "vuex";
import kaapanaApiService from '@/common/kaapanaApi.service'

export default Vue.extend({
  data: () => ({
    loading: true,
    launchedAppLinks: [] as any,
    headers: [
      {
        text: "Name",
        align: "start",
        value: "link",
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
      { text: "Action", value: "releaseMame" },
    ],
  }),
  mounted() {
    this.loading = true;
    this.getHelmCharts()
    this.loading = false;
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', "commonData", "launchApplicationData", "availableApplications"])
  
  },
  methods: {

    getHelmCharts() {
      this.loading = true;
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

    deleteChart(releaseName: any) {
      let params = {
        release_name: releaseName,
      };
      this.loading = true;
      kaapanaApiService
        .helmApiGet("/helm-delete-chart", params)
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
</style>
