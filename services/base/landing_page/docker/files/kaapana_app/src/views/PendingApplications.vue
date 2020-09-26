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
            a(:href='item.link', target='_blank') {{ item.name }}
          template(v-slot:item.name="{ item }")
            v-btn(
              @click="uninstallChart(item.name)",
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
    loading: false,
    launchedAppLinks: [] as any,
    headers: [
      {
        text: "Name",
        align: "start",
        value: "link",
      },
      { text: "Action", value: "name" },
    ],
  }),
  mounted() {
    this.getHelmCharts()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', "commonData", "launchApplicationData", "availableApplications"])
  
  },
  methods: {

    getHelmCharts() {
      kaapanaApiService
        .helmApiGet("/pending-applications", {})
        .then((response: any) => {
          this.launchedAppLinks = response.data;
        })
        .catch((err: any) => {
          console.log(err);
        });
    },

    uninstallChart(releaseName: any) {
      let params = {
        release_name: releaseName,
      };
      kaapanaApiService
        .helmApiGet("/helm-uninstall-chart", params)
        .then((response: any) => {
          this.loading = true;
          setTimeout(() => {
            this.getHelmCharts();
            this.loading = false;
          }, 1000);
        })
        .catch((err: any) => {
          console.log(err);
        });
    },
  }
})
</script>

<style lang="scss">
</style>
