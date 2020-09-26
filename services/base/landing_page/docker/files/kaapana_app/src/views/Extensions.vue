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
        template(v-slot:item.name="{ item }")
          a(:href='item.link', target='_blank') {{ item.name }}
        template(v-slot:item.installed="{ item }")
          v-btn(
            @click="uninstallChart(item.name)",
            color="primary",
             v-if="item.installed==='yes'"
          ) Uninstall
          v-btn(
            @click="installChart(item.name, item.version, item.multi_installable)",
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
        value: "name",
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
    this.getHelmCharts();
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

    installChart(name: any, version: any, multi_installable: any) {
      let payload = {
        'name': name,
        'version': version,
        'multi_installable': multi_installable
      }
      this.loading = true;
      kaapanaApiService
        .helmApiPost("/helm-install-extension", payload)
        .then((response: any) => {
            this.loading = false;
            this.getHelmCharts();
        })
        .catch((err: any) => {
          console.log(err);
        });
    },
  },
});
</script>

<style lang="scss">
</style>
