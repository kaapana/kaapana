<template lang="pug">
  .workflow-applications
    v-container(grid-list-lg text-left)
      div
        h2 Pending Application List
        p If a workflow has started an application, you will find here the corresponding url to the application
          span(v-for='link in applicationsLinks', :key='link.id')
            br
            a(:href='link' target='_blank') {{link}}
        h2 Launch an application manually (max 10 applications at the same time)
        p
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
          template(v-slot:item.runId='{ item }')
            v-btn(@click='uninstallChart(item.runId)', color="primary") Shutdown app
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
      { text: 'Action', value: 'runId'},
    ],
  }),
  mounted() {
    this.getApplicationsLinks()
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated', "commonData", "launchApplicationData", "availableApplications"])
  
  },
  methods: {
    //Todo remove Traefik routes...here
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
              this.applicationsLinks.push(location.protocol + '//' + location.host + backendRoutes[i])
          }
          if (backendRoutes[i].includes('desktop')) {
              this.launchedAppLinks.push({
                url: location.protocol + '//' + location.host + backendRoutes[i],
                runId: backendRoutes[i].slice(-30)
              })
          } else if (backendRoutes[i] == '/code') {
              this.launchedAppLinks.push({
                url: location.protocol + '//' + location.host + backendRoutes[i],
                runId: 'code-server'
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
    },

    // deleteApplication(run_id: any) {
    //   let payload = {
    //     'run_id': run_id,
    //     'namespace': 'flow-jobs'
    //   }
    //   kaapanaApiService.deleteApplication(payload).then((response: any) => {
    //     this.loading = true
    //     setTimeout(() => {
    //       this.getDagRuns()
    //       this.loading = false
    //     }, 1000);
    //   }).catch((err: any) => {
    //     console.log(err)
    //   })
    // },

    // getDagRuns(){
    //   kaapanaApiService.getDagRuns().then((response: any) => {
    //     this.launchedAppLinks = []
    //     for (const idx in response.data) {
    //       let params = {run_id: response.data[idx].run_id, namespace: 'flow-jobs'}
    //       kaapanaApiService.getIngressByRunId(params).then((response: any) => {
    //         if (response != 'deleted') {
    //           let d = new Date(response.data.metadata.creation_timestamp)
    //           let diff = d.getTime()+12*60*60*1000-Date.now()
    //           let hours = Math.floor(diff/(60*60*1000))
    //           let minutes = Math.floor((diff-hours*60*60*1000)/(60*1000)) 
    //           this.launchedAppLinks.push({
    //             url: response.data.spec.rules[0].http.paths[0].path, 
    //             runId: response.data.metadata.labels.run_id,
    //             appTimeout: hours + 'h' + minutes + 'm'
    //           })
    //         }
    //       }).catch((err: any) => {
    //         console.log(err)
    //       })
    //     } 
    //   }).catch((err: any) => {
    //     console.log(err)
    //   })
    // },

    // launchApplication(applicationName: any) {
    //   function uuidv4() {
    //     return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    //       var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    //       return v.toString(16);
    //     });
    //   }

    //   if (this.launchedAppLinks.length < 10) {
    //     let payload = JSON.parse(JSON.stringify(this.launchApplicationData[applicationName]))
    //     payload["conf"]["ingress_path"] = payload["conf"]["ingress_path"] + "-" + uuidv4() + '-' + this.currentUser.username,

    //     kaapanaApiService.launchApplication(payload).then((response: any) => {
    //       this.loading = true
    //       setTimeout(() => {
    //         this.getDagRuns()
    //         this.loading = false
    //       }, 15000);
    //     }).catch((err: any) => {
    //       console.log(err)
    //     })
    //   }
    // }
  }
})
</script>

<style lang="scss">
</style>
