<template lang="pug">
  .workflow-applications
    v-container(grid-list-lg text-left)
      div
        h2 List of applications started in a workflow (max 2 applications at the same time)
        p If a workflow has started an application, you will find here the corresponding url to the application. Once you are done you can here finish the manual interaction which will continue the workflow.
        v-data-table.elevation-1(:headers='headers' :items='applicationsLinks' :items-per-page='20' :loading='loading' loading-text="Waiting a few seconds...")
          template(v-slot:item.url='{ item }')
            a(:href='item.url', target='_blank') {{ item.url }}
          template(v-slot:item.chartReleaseName='{ item }')
            v-btn(@click='uninstallChart(item.chartReleaseName)', color="primary") Finished manual interaction
        br
        br
        h2 Launch an application manually (max 10 applications at the same time)
        p If you want to work 
        v-menu(offset-y='')
          template(v-slot:activator='{ on, attrs }')
            v-btn(color='primary' dark='' v-bind='attrs' v-on='on')
              | Select application you want to launch
          v-list
            v-list-item(v-for='(item, index) in availableApplications' :key='index' @click="installChart(item)")
              v-list-item-title {{ item }}
        v-data-table.elevation-1(:headers='headers' :items='launchedAppLinks' :items-per-page='20' :loading='loading' loading-text="Waiting a few seconds...")
          template(v-slot:item.url='{ item }')
            a(:href='item.url', target='_blank') {{ item.url }}
          template(v-slot:item.chartReleaseName='{ item }')
            v-btn(@click='uninstallChart(item.chartReleaseName)', color="primary") Shutdown app
</template>

<script lang="ts">
import Vue from 'vue';
import request from '@/request';
import { mapGetters } from "vuex";
import kaapanaApiService from '@/common/kaapanaApi.service'

export default Vue.extend({
  data: () => ({
    loading: false,
    applicationsLinks: [] as any,
    launchedAppLinks: [] as any,
    headers: [
      {
        text: 'Links',
        align: 'start',
        value: 'url',
      },
      { text: 'Action', value: 'chartReleaseName'},
    ],
  }),
  mounted() {
    this.getApplicationsLinks()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', "commonData", "launchApplicationData", "availableApplications"])
  
  },
  methods: {

    getTraefikBackendRoutes() {
      return new Promise((resolve, reject) => {
        let traefikUrl = ''
        if (Vue.config.productionTip === true) {
          traefikUrl = '/traefik/api/http/routers'
        } else {
          traefikUrl = '/jsons/testingTraefikResponse.json'
        }

        request.get(traefikUrl).then(response => {
          let allRoutes = []
          for (const routes in response.data) {
            if (response.data[routes]['status'] == 'enabled') {
              allRoutes.push(response.data[routes]['rule'].slice(12,-2))
            }
          }
          resolve(allRoutes)
        }).catch(error => {
          console.log('Something went wrong with traefik', error)
          reject(error)
        })

      })
    },

    getApplicationsLinks() {
      this.getTraefikBackendRoutes().then((backendRoutes: any) => {
        backendRoutes = [...new Set(backendRoutes)]
        // checks only for dynamic and desktop prefix
        this.applicationsLinks = []
        this.launchedAppLinks = []
        for (var i = 0; i < backendRoutes.length; i++) {
          if (backendRoutes[i].includes('dynamic')) {
              this.applicationsLinks.push({
                url: location.protocol + '//' + location.host + backendRoutes[i],
                chartReleaseName: backendRoutes[i].slice(1)
              })

          }
          if (backendRoutes[i].includes('desktop')) {
              this.launchedAppLinks.push({
                url: location.protocol + '//' + location.host + backendRoutes[i],
                chartReleaseName: backendRoutes[i].slice(-30)
              })
          } else if (backendRoutes[i] == '/code') {
              this.launchedAppLinks.push({
                url: location.protocol + '//' + location.host + backendRoutes[i],
                chartReleaseName: 'code-server'
              })
          }
        }
        console.log('assd', this.launchedAppLinks)
      })
    },

    uninstallChart(run_id: any) {
      let params = {
        'chart': run_id
      }
      kaapanaApiService.helmApiGet('/helm-uninstall-chart', params).then((response: any) => {
        this.loading = true
        setTimeout(() => {
          this.getApplicationsLinks()
          this.loading = false
        }, 1000);
      }).catch((err: any) => {
        console.log(err)
      })

    },

    installChart(applicationName: any) {
      function uuidv4() {
        return 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
      }

      if (this.launchedAppLinks.length < 10) {
        let payload = JSON.parse(JSON.stringify(this.launchApplicationData[applicationName]))
        // let payload =JSON.parse(JSON.stringify({
        //     "repoName": "kaapana-public",
        //     "chartName": "jupyterlab",
        //     "version": "1.0-vdev",
        //     "sets": {
        //         "mount_path": "/home/data/jupyterlab",
        //         "ingress_path": "/jupyterlab"
        //     }
        // }))
        let identifier = uuidv4()
        if (payload["sets"]["ingress_path"] != '/code') {
          payload["sets"]["ingress_path"] = payload["sets"]["ingress_path"] + "-desktop-" + this.currentUser.username + "-" + identifier
          payload["sets"]["multi_instance_suffix"] = identifier
          payload["customName"] = identifier
        }
        console.log(payload)
        kaapanaApiService.helmApiPost('/helm-install-chart', payload).then((response: any) => {
          this.loading = true
          setTimeout(() => {
            this.getApplicationsLinks()
            this.loading = false
          }, 15000);
        }).catch((err: any) => {
          console.log(err)
        })
      }
    }
  }
})
</script>

<style lang="scss">
</style>
