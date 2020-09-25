<template lang="pug">
.workflow-applications
  v-container(grid-list-lg, text-left)
    div
      h2 Extensions
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
    applicationsLinks: [] as any,
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
      // API calls to go from here
      //hello santshosh
      const responseJson = [
        {
          name: "kaapana/code-server",
          description: "chart 1",
          app_version: "1",
          version: "1.0",
          link: "asddd",
          installed: 'no',
          multi_installable: 'no',

          // installed_name: "jupyterlab",
          // install_json: {
          //   repoName: "kaapana-public",
          //   chartName: "jupyterlab",
          //   version: "1.0-vdev",
          //   sets: {},
          // },
        },
        {
          name: "kaapana/jupyterlab",
          description: "chart 2",
          app_version: "1",
          version: "1.2",
          link: "awwe",
          installed: 'yes',
          multi_installable: 'yes'
          // installed_name: "",
          // install_json: {
          //   repoName: "kaapana-public",
          //   chartName: "jupyterlab",
          //   version: "1.0-vdev",
          //   sets: {
          //     mount_path: "/home/data/jupyterlab",
          //     ingress_path: "/jupyterlab",
          //   },
          // },
        },
      ];

      let params = {
        repo: "kaapana-public",
      };

      //this.launchedAppLinks = responseJson;

      kaapanaApiService
        .helmApiGet("/all-available-charts", params)
        .then((response: any) => {
          //this.launchedAppLinks = responseJson;
          this.launchedAppLinks = response.data;
        })
        .catch((err: any) => {
          console.log(err);
        });
    },


    uninstallChart(installed_name: any) {
      let params = {
        chart: installed_name,
      };
      let helmUninstallChart = "";

      if (Vue.config.productionTip === true) {
        helmUninstallChart = "/helm-uninstall-chart";
      } else {
        helmUninstallChart = "/kube-helm-api/helm-uninstall-chart.json";
      }

      kaapanaApiService
        .helmApiGet(helmUninstallChart, params)
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

    // installChart(applicationName: any) {
    //   function uuidv4() {
    //     return 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    //       var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    //       return v.toString(16);
    //     });
    //   }

    //   if (this.launchedAppLinks.length < 10) {
    //     let payload = JSON.parse(JSON.stringify(this.launchApplicationData[applicationName]))
    //     // let payload =JSON.parse(JSON.stringify({
    //     //     "repoName": "kaapana-public",
    //     //     "chartName": "jupyterlab",
    //     //     "version": "1.0-vdev",
    //     //     "sets": {
    //     //         "mount_path": "/home/data/jupyterlab",
    //     //         "ingress_path": "/jupyterlab"
    //     //     }
    //     // }))
    //     let identifier = uuidv4()
    //     if (payload["sets"]["ingress_path"] != '/code') {
    //       payload["sets"]["ingress_path"] = payload["sets"]["ingress_path"] + "-desktop-" + this.currentUser.username + "-" + identifier
    //       payload["sets"]["multi_instance_suffix"] = identifier
    //       payload["customName"] = identifier
    //     }
    //     console.log(payload)
    //     kaapanaApiService.helmApiPost('/helm-install-chart', payload).then((response: any) => {
    //       this.loading = true
    //       setTimeout(() => {
    //         this.getApplicationsLinks()
    //         this.loading = false
    //       }, 15000);
    //     }).catch((err: any) => {
    //       console.log(err)
    //     })
    //   }
    // },

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
