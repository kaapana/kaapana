<template lang="pug">
.workflow-applications
  v-container(grid-list-lg, text-left)
    v-card
      v-card-title
        v-row()
          v-col(cols='12' sm='5')
            span Applications and workflows &nbsp;
              v-tooltip(bottom='')
                template(v-slot:activator='{ on, attrs }')
                  v-icon(@click="updateExtensions()", color='primary' dark='' v-bind='attrs' v-on='on')
                    | mdi-cloud-download-outline
                span By clicking on this icon it will try to download the latest extensions. In case you do not have internet connection this can also be done on the terminal via ./install-platform --update-extensions.
            br
            span(style='font-size: 14px') In readthedocs you find a description of each application and workflow
          v-col(cols='12' sm='2')
            v-select(label='Kind' :items="['All', 'Workflows', 'Applications']" v-model='extensionKind' hide-details='')
          v-col(cols='12' sm='2')
            v-select(label='Version' :items="['All', 'Stable', 'Experimental']" v-model='extensionExperimental' hide-details='')
          v-col(cols='12' sm='3')
            v-text-field(v-model='search' append-icon='mdi-magnify' label='Search' hide-details='')
       
      v-data-table.elevation-1(
        :headers="headers",
        :items="filteredLaunchedAppLinks",
        :items-per-page="20",
        :loading="loading",
        :search='search',
        sort-by='releaseMame',
        loading-text="Waiting a few seconds..."
      )
        template(v-slot:item.releaseMame="{ item }")
          span {{ item.releaseMame }} &nbsp;
            a(:href='link', target='_blank' v-for="link in item.links" :key="item.link")
              v-icon(color='primary') mdi-open-in-new
        template(v-slot:item.versions="{ item }")  
          v-select(v-if="item.installed==='no'" :items="item.versions" v-model="item.version" hide-details='')
          span(v-if="item.installed==='yes'") {{ item.version }}
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
        template(v-slot:item.experimental="{ item }")
          v-tooltip(bottom='' v-if="item.experimental==='yes'")
            template(v-slot:activator='{ on, attrs }')
              v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                | mdi-test-tube
            span Experimental extension or DAG, not tested yet!
        template(v-slot:item.installed="{ item }")
          v-btn(
            @click="deleteChart(item.releaseMame, item.name, item.version, item.keywords)",
            color="primary",
             v-if="item.installed==='yes'"
          ) 
            span(v-if="item.multiinstallable ==='yes'") Delete 
            span(v-if="item.multiinstallable ==='no'") Uninstall
          v-btn(
            @click="installChart(item.name, item.version, item.keywords)",
            color="primary",
            v-if="item.installed==='no'"
          ) 
            span(v-if="item.multiinstallable ==='yes'") Launch
            span(v-if="item.multiinstallable ==='no'") Install
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
    search: '',
    extensionExperimental: 'Stable',
    extensionKind: 'All',
    headers: [
      {
        text: "Name",
        align: "start",
        value: "releaseMame",
      },
      {
        text: "Version",
        align: "start",
        value: "versions",
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
        value: "helmStatus",
      },
      {
        text: "Kube Status",
        align: "start",
        value: "kubeStatus",
      },
      {
        text: "Experimental",
        align: "start",
        value: "experimental",
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
    this.getHelmCharts();
  },
  computed: {
    filteredLaunchedAppLinks(): any {
      return this.launchedAppLinks.filter((i: any) => {
        let experimentalFilter = true
        let kindFilter = true
        if (this.extensionExperimental=='Stable' && i.experimental==='yes') {
          experimentalFilter = false
        } else if (this.extensionExperimental=='Experimental' && i.experimental==='no') {
          experimentalFilter = false
        }

        if (this.extensionKind=='Workflows' && i.kind==='extension') {
          kindFilter = false
        } else if (this.extensionKind=='Applications' && i.kind==='dag') {
          kindFilter = false
        }
        return experimentalFilter && kindFilter
      })
    },

    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "commonData",
      "launchApplicationData",
      "availableApplications",
    ])
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

    updateExtensions() {
      this.loading = true;
      kaapanaApiService
        .helmApiGet("/helm-repo-update", {})
        .then((response: any) => {
          this.getHelmCharts();
          this.loading = false;
          alert(response.data)
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
