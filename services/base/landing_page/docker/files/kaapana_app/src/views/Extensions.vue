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
          a(:href='item.link', target='_blank') {{ item.releaseMame }}
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
    loading: false,
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
        text: "Description",
        align: "start",
        value: "description",
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
            this.getHelmCharts();
            //this.loading = false;
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
</style>
