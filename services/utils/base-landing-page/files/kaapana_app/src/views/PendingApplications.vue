<template lang="pug">
  .workflow-applications
    v-container(grid-list-lg text-left)
      v-card
        v-card-title
          | List of applications started in a workflow &nbsp;
          v-tooltip(bottom='')
            template(v-slot:activator='{ on, attrs }')
              v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                | mdi-information-outline
            span If a workflow has started an application, you will find here the corresponding url to the application. Once you are done you can here finish the manual interaction which will continue the workflow.
          v-spacer
          v-text-field(v-model='search' append-icon='mdi-magnify' label='Search' single-line='' hide-details='')
        v-data-table.elevation-1(
          :headers="headers",
          :items="launchedAppLinks",
          :items-per-page="20",
          :loading="loading",
          sort-by='releaseName',
          loading-text="Waiting a few seconds..."
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
a {  text-decoration: none;}
</style>